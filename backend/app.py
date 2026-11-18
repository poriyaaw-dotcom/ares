from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
import hashlib
import hmac
import os
import re
import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger("ares")

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "requests.db")))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "600"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "5"))
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", "12000"))
HMAC_SECRET = os.getenv("HMAC_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() == "true"

ALLOWED_SERVICES = {
    "طراحی وب‌سایت شرکتی",
    "طراحی وب‌سایت فروشگاهی",
    "UI/UX",
    "بهینه سازی",
    "سئو (SEO)",
    "پشتیبانی",
    "سایر",
}

PHONE_RE = re.compile(r"^(?:\+98|0098|98|0)?9\d{9}$")

if not HMAC_SECRET:
    raise RuntimeError("HMAC_SECRET is required. Copy .env.example to .env and set a long random secret.")

DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


def db_connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def init_db() -> None:
    with closing(db_connect()) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS contact_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                service TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                client_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new'
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_contact_requests_client_time "
            "ON contact_requests(client_hash, created_at)"
        )
        db.commit()


def normalize_phone(value: str) -> str:
    # Keep the public form deliberately strict: ASCII digits only, with an optional +98 prefix.
    value = value.strip()
    if any(ch not in "+0123456789" for ch in value):
        return ""
    value = re.sub(r"[\s\-()]", "", value)
    if value.startswith("0098"):
        value = "+98" + value[4:]
    elif value.startswith("98") and not value.startswith("+98"):
        value = "+" + value
    return value


def get_client_hash(request: Request) -> str:
    # We intentionally do not store the visitor's raw IP. Forwarded headers are trusted only when
    # the deployment explicitly opts in (and should only be enabled behind a trusted proxy).
    ip = request.client.host if request.client else "unknown"
    if TRUST_PROXY:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        if forwarded_for:
            ip = forwarded_for.split(",", 1)[0].strip() or ip
    return hmac.new(HMAC_SECRET.encode(), ip.encode(), hashlib.sha256).hexdigest()


def rate_limit_cutoff() -> str:
    return datetime.fromtimestamp(
        datetime.now(timezone.utc).timestamp() - RATE_LIMIT_WINDOW_SECONDS,
        tz=timezone.utc,
    ).isoformat()


def save_contact_request(payload: "ContactRequest", client_hash: str, now: str) -> int:
    # One write transaction makes the rate-limit check + insert atomic under concurrent requests.
    with closing(db_connect()) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            row = db.execute(
                "SELECT COUNT(*) AS count FROM contact_requests "
                "WHERE client_hash = ? AND created_at >= ?",
                (client_hash, rate_limit_cutoff()),
            ).fetchone()
            if int(row["count"]) >= RATE_LIMIT_MAX_REQUESTS:
                db.rollback()
                raise HTTPException(
                    status_code=429,
                    detail="تعداد درخواست‌ها زیاد است. لطفاً چند دقیقه بعد دوباره تلاش کنید.",
                )

            cursor = db.execute(
                """
                INSERT INTO contact_requests
                (name, phone, service, message, created_at, client_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (payload.name, payload.phone, payload.service, payload.message, now, client_hash),
            )
            request_id = int(cursor.lastrowid)
            db.commit()
            return request_id
        except Exception:
            if db.in_transaction:
                db.rollback()
            raise


class ContactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=8, max_length=20)
    service: str = Field(min_length=1, max_length=60)
    message: str = Field(default="", max_length=2000)
    website: str = Field(default="", max_length=100)  # honeypot; must remain empty

    @field_validator("name", "message", mode="before")
    @classmethod
    def clean_text(cls, value):
        if not isinstance(value, str):
            raise ValueError("Invalid text")
        return value.strip()

    @field_validator("service")
    @classmethod
    def valid_service(cls, value: str) -> str:
        value = value.strip()
        if value not in ALLOWED_SERVICES:
            raise ValueError("Invalid service")
        return value

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        value = normalize_phone(value)
        if not PHONE_RE.fullmatch(value):
            raise ValueError("Invalid phone number")
        return value


class BodySizeLimitMiddleware:
    """Reject request bodies above the configured limit, including chunked uploads."""

    def __init__(self, app: ASGIApp, max_body_size: int):
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        content_length = next(
            (value for key, value in scope.get("headers", []) if key.lower() == b"content-length"),
            None,
        )
        if content_length:
            try:
                if int(content_length) > self.max_body_size:
                    await self._too_large(send)
                    return
            except ValueError:
                await self._bad_content_length(send)
                return

        chunks: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue

            body = message.get("body", b"")
            total += len(body)
            if total > self.max_body_size:
                await self._too_large(send)
                return

            if body:
                chunks.append(body)
            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        sent = False

        async def replay_receive() -> Message:
            nonlocal sent
            if sent:
                return {"type": "http.disconnect"}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay_receive, send)

    async def _too_large(self, send: Send) -> None:
        body = b'{"detail":"Request too large"}'
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()), (b"cache-control", b"no-store")],
        })
        await send({"type": "http.response.body", "body": body})

    async def _bad_content_length(self, send: Send) -> None:
        body = b'{"detail":"Invalid Content-Length"}'
        await send({
            "type": "http.response.start",
            "status": 400,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()), (b"cache-control", b"no-store")],
        })
        await send({"type": "http.response.body", "body": body})


app = FastAPI(
    title="ARES Contact API",
    docs_url=None if ENVIRONMENT == "production" else "/docs",
    redoc_url=None if ENVIRONMENT == "production" else "/redoc",
)

app.add_middleware(BodySizeLimitMiddleware, max_body_size=MAX_BODY_BYTES)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Serve the existing frontend assets without changing their paths.
for _asset_dir in ("css", "js", "images", "img", "assets", "fonts", "logo"):
    _asset_path = BASE_DIR / _asset_dir
    if _asset_path.is_dir():
        app.mount(f"/{_asset_dir}", StaticFiles(directory=_asset_path), name=_asset_dir)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'sha256-O8Hp/aMHqLpePwWb0aQvWhYATF0a6sMAoAb/5BAnfVw='; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    if ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/logo/{filename}", include_in_schema=False)
async def logo(filename: str):
    # Serve the existing logo explicitly so the frontend logo works even if
    # StaticFiles mounting behaves differently across environments.
    if filename != "YOUR-LOGO.png":
        raise HTTPException(status_code=404, detail="Logo not found")
    logo_path = BASE_DIR / "logo" / filename
    if not logo_path.is_file():
        raise HTTPException(status_code=404, detail="Logo not found")
    return FileResponse(logo_path)


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(BASE_DIR / "index.html")


FRONTEND_PAGES = {
    "about": "about.html",
    "service-corporate": "service-corporate.html",
    "service-ecommerce": "service-ecommerce.html",
    "service-uiux": "service-uiux.html",
    "service-optimization": "service-optimization.html",
    "service-seo": "service-seo.html",
    "service-support": "service-support.html",
}


@app.get("/{page_name}.html", include_in_schema=False)
async def frontend_page(page_name: str):
    filename = FRONTEND_PAGES.get(page_name)
    if not filename:
        raise HTTPException(status_code=404, detail="Page not found")
    page_path = BASE_DIR / filename
    if not page_path.is_file():
        raise HTTPException(status_code=404, detail="Page not found")
    return FileResponse(page_path)


async def send_telegram_notification(text: str, request_id: int) -> None:
    """Try Telegram without allowing notification failure to affect the request."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            result = await client.post(
                telegram_url,
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            )
            result.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("Telegram notification timed out for request_id=%s", request_id)
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500].replace("\n", " ")
        logger.warning(
            "Telegram rejected notification for request_id=%s: HTTP %s: %s",
            request_id,
            exc.response.status_code,
            body,
        )
    except httpx.RequestError as exc:
        logger.warning(
            "Could not reach Telegram for request_id=%s: %s",
            request_id,
            exc.__class__.__name__,
        )


def _send_email_sync(subject: str, body: str) -> None:
    """Synchronous Gmail SMTP operation, run in a worker thread."""
    message = EmailMessage()
    message["From"] = SMTP_USERNAME
    message["To"] = NOTIFICATION_EMAIL
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=12) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)


async def send_email_notification(
    subject: str, body: str, request_id: int
) -> None:
    """Try email without allowing notification failure to affect the request."""
    if not all((SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, NOTIFICATION_EMAIL)):
        logger.warning(
            "Email notification is not configured; request_id=%s", request_id
        )
        return

    try:
        await asyncio.to_thread(_send_email_sync, subject, body)
    except (OSError, smtplib.SMTPException) as exc:
        logger.warning(
            "Could not send email for request_id=%s: %s",
            request_id,
            exc.__class__.__name__,
        )


@app.post("/api/contact")
async def create_contact(payload: ContactRequest, request: Request):
    # Honeypot: bots that fill the hidden field are silently rejected.
    if payload.website:
        return {"ok": True}

    client_hash = get_client_hash(request)
    now = datetime.now(timezone.utc).isoformat()
    request_id = save_contact_request(payload, client_hash, now)

    notification_text = (
        "🔔 درخواست همکاری جدید\n\n"
        f"👤 نام: {payload.name}\n"
        f"📱 شماره: {payload.phone}\n"
        f"🛠 خدمت: {payload.service}\n"
        f"💬 توضیحات: {payload.message or 'بدون توضیح'}\n\n"
        f"🆔 شماره درخواست: {request_id}"
    )

    # both channels work ... they dont mess with each other ...telegram dont work cause of IRAN -_-
    await send_telegram_notification(notification_text, request_id)

    email_body = (
        "درخواست همکاری جدید از سایت ARES\n\n"
        f"نام: {payload.name}\n"
        f"شماره تماس: {payload.phone}\n"
        f"خدمت: {payload.service}\n"
        f"توضیحات: {payload.message or 'بدون توضیح'}\n\n"
        f"شماره درخواست: {request_id}\n"
        f"زمان ثبت: {now}"
    )
    await send_email_notification(
        f"🔔 درخواست جدید ARES #{request_id}",
        email_body,
        request_id,
    )

    return {"ok": True, "request_id": request_id}


@app.get("/api/health", include_in_schema=False)
async def health():
    return {"ok": True}
