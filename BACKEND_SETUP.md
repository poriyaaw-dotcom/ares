# ARES backend setup

## Local `.env`

Create `.env` from `.env.example` and set:

- `HMAC_SECRET` — a long random secret.
- `TELEGRAM_BOT_TOKEN` — your BotFather token.
- `TELEGRAM_CHAT_ID` — your Telegram chat ID.
- `SMTP_HOST=smtp.gmail.com`
- `SMTP_PORT=587`
- `SMTP_USERNAME` — the Gmail address that sends the notification.
- `SMTP_PASSWORD` — the Google App Password (not the normal Gmail password).
- `NOTIFICATION_EMAIL` — the Gmail address that receives the notification.
- `TRUST_PROXY=false` — leave this false unless the app is behind a trusted reverse proxy that you control. If enabled, the first `X-Forwarded-For` address is used for rate limiting.

Keep `.env` private and never commit it to Git.

## Notifications

The contact request is saved to SQLite before notifications are attempted.
Telegram and email are attempted independently, so a Telegram connection failure
does not prevent email, and an email failure does not prevent Telegram.

## Security notes

- The contact endpoint validates all fields server-side and rejects unknown fields.
- Phone numbers are restricted to ASCII digits with the supported Iranian prefixes.
- The honeypot field is silently accepted for bot submissions without saving them.
- Rate-limit checking and insertion happen inside one SQLite write transaction, so concurrent requests cannot race the limit check.
- Request bodies are capped before application parsing, including chunked requests.
- API responses are marked `no-store` and `noindex`.
- Security headers include CSP, HSTS in production, clickjacking protection, MIME sniffing protection, referrer restrictions, and cross-origin isolation policies.
- The SQLite database is local state and is created automatically on startup.
- For deployment, serve the app through HTTPS and keep the reverse proxy's forwarded-header configuration locked down to trusted proxies only.

## Production checklist

1. Set `ENVIRONMENT=production`.
2. Generate a new, long random `HMAC_SECRET` for the server.
3. Use a Google App Password for SMTP rather than the account password.
4. Keep `.env` outside source control and restrict its filesystem permissions.
5. Put FastAPI behind an HTTPS reverse proxy and configure forwarded headers only for that proxy.
6. Back up `data/requests.db` securely; it contains contact submissions.
7. Do not expose `/docs` or `/redoc` in production (they are disabled automatically).
8. Keep Python dependencies updated and review security advisories before upgrades.
9. Run the application as a dedicated non-root user with only the filesystem permissions it needs.
10. Rotate notification credentials immediately if they are ever exposed.

Start locally with:

`python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000`
