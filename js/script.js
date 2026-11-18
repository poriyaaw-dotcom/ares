/* =====================================================
   ARES WEBSITE JAVASCRIPT
===================================================== */

document.addEventListener("DOMContentLoaded", () => {

    /* =================================================
       DARK MODE
       Persists the user's choice across all ARES pages.
       Now handles both desktop and mobile toggles.
    ================================================= */

    const themeToggle = document.querySelector(".theme-toggle");
    const mobileThemeToggle = document.querySelector(".mobile-theme-toggle");
    const savedTheme = localStorage.getItem("ares-theme");
    const prefersDark = window.matchMedia &&
        window.matchMedia("(prefers-color-scheme: dark)").matches;

    const setTheme = (dark, save = true) => {
        document.documentElement.classList.add("theme-ready");
        document.body.classList.toggle("dark-mode", dark);

        if (themeToggle) {
            themeToggle.setAttribute("aria-pressed", String(dark));
            themeToggle.setAttribute(
                "aria-label",
                dark ? "فعال کردن حالت روشن" : "فعال کردن حالت تاریک"
            );
            themeToggle.setAttribute(
                "title",
                dark ? "حالت روشن" : "حالت تاریک"
            );
        }

        if (save) {
            localStorage.setItem("ares-theme", dark ? "dark" : "light");
        }
    };

    setTheme(
        savedTheme === "dark" ||
        (savedTheme === null && prefersDark),
        false
    );

    const handleThemeClick = () => setTheme(!document.body.classList.contains("dark-mode"));
    if (themeToggle) themeToggle.addEventListener("click", handleThemeClick);
    if (mobileThemeToggle) mobileThemeToggle.addEventListener("click", handleThemeClick);



    /* =================================================
       MOBILE MENU
    ================================================= */

    const menuButton = document.querySelector(".mobile-menu-button");
    const mobileNavigation = document.querySelector(".mobile-navigation");

    if (menuButton && mobileNavigation) {

        menuButton.addEventListener("click", () => {

            mobileNavigation.classList.toggle("open");

        });


        const mobileLinks =
            mobileNavigation.querySelectorAll("a");

        mobileLinks.forEach((link) => {

            link.addEventListener("click", () => {

                mobileNavigation.classList.remove("open");

            });

        });

    }


    /* =================================================
       ACTIVE NAVIGATION
    ================================================= */

    const sections =
        document.querySelectorAll("main section[id]");

    const navLinks =
        document.querySelectorAll(".nav-link");

    const updateActiveNavigation = () => {

        let currentSection = "";

        const scrollPosition =
            window.scrollY + 180;


        sections.forEach((section) => {

            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;

            if (
                scrollPosition >= sectionTop &&
                scrollPosition < sectionTop + sectionHeight
            ) {

                currentSection = section.getAttribute("id");

            }

        });


        navLinks.forEach((link) => {

            link.classList.remove("active");

            const href = link.getAttribute("href");

            if (href === `#${currentSection}`) {

                link.classList.add("active");

            }

        });

    };


    window.addEventListener(
        "scroll",
        updateActiveNavigation
    );

    updateActiveNavigation();


    /* =================================================
       HEADER SHADOW ON SCROLL
    ================================================= */

    const header = document.querySelector(".header");

    const updateHeader = () => {

        if (!header) return;

        if (window.scrollY > 30) {

            header.style.boxShadow =
                "0 5px 25px rgba(0, 0, 0, 0.06)";

        } else {

            header.style.boxShadow = "none";

        }

    };

    window.addEventListener(
        "scroll",
        updateHeader
    );

    updateHeader();


    /* =================================================
       SMOOTH SCROLL
    ================================================= */

    document
        .querySelectorAll('a[href^="#"]')
        .forEach((link) => {

            link.addEventListener("click", (event) => {

                const targetId =
                    link.getAttribute("href");

                if (
                    !targetId ||
                    targetId === "#"
                ) {
                    return;
                }

                const target =
                    document.querySelector(targetId);

                if (!target) {
                    return;
                }

                event.preventDefault();

                target.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });

            });

        });


    /* =================================================
       SIMPLE REVEAL ANIMATION
    ================================================= */

    const revealElements =
        document.querySelectorAll(
            ".service-card, .process-item, .about-content, .about-box, .contact-box"
        );


    revealElements.forEach((element) => {

        element.style.opacity = "0";

        element.style.transform =
            "translateY(25px)";

        element.style.transition =
            "opacity 0.7s ease, transform 0.7s ease";

    });


    const revealObserver =
        new IntersectionObserver(
            (entries, observer) => {

                entries.forEach((entry) => {

                    if (!entry.isIntersecting) {
                        return;
                    }

                    entry.target.style.opacity = "1";

                    entry.target.style.transform =
                        "translateY(0)";

                    observer.unobserve(
                        entry.target
                    );

                });

            },
            {
                threshold: 0.12
            }
        );


    revealElements.forEach((element) => {

        revealObserver.observe(element);

    });


    /* =================================================
       PHONE NUMBER
       The HTML tel: link already makes it clickable.
    ================================================= */

    const phoneLinks =
        document.querySelectorAll(
            'a[href^="tel:"]'
        );

    phoneLinks.forEach((link) => {

        link.setAttribute(
            "aria-label",
            "تماس تلفنی"
        );

    });


    /* =================================================
       ESCAPE KEY - CLOSE MOBILE MENU
    ================================================= */

    document.addEventListener(
        "keydown",
        (event) => {

            if (
                event.key === "Escape" &&
                mobileNavigation
            ) {

                mobileNavigation.classList.remove(
                    "open"
                );

            }

        }
    );

    /* =================================================
       SERVICES VIEW
       The section is compact enough to show the complete
       desktop service grid when the nav item is clicked.
    ================================================= */

    const servicesLink = document.querySelector(
        '.nav-link[href="#services"]'
    );

    if (servicesLink) {
        servicesLink.addEventListener("click", () => {
            document.body.classList.add("services-focused");
        });
    }

    document.querySelectorAll(
        '.nav-link:not([href="#services"])'
    ).forEach((link) => {
        link.addEventListener("click", () => {
            document.body.classList.remove("services-focused");
        });
    });


    /* =================================================
       CONSULTATION LINKS
       Header / hero / about-page buttons open the form.
    ================================================= */

    const openConsultationFormFromLink = (event) => {
        const link = event.currentTarget;
        const href = link.getAttribute("href") || "";

        if (!href.endsWith("#contact-form")) return;

        // On another page, let the browser navigate to the home page.
        // The home-page hash handler will open the form exactly once.
        if (!document.querySelector("#contact")) return;

        event.preventDefault();

        const contact = document.querySelector("#contact");
        const formToggle = document.querySelector(".contact-form-toggle");
        if (!contact || !formToggle) return;

        // One immediate position update only. No second scroll after opening.
        window.scrollTo({
            top: contact.getBoundingClientRect().top + window.scrollY - 90,
            behavior: "auto"
        });

        if (formToggle.getAttribute("aria-expanded") !== "true") {
            formToggle.click();
        }
    };

    document.querySelectorAll("a.consultation-link").forEach((link) => {
        link.addEventListener("click", openConsultationFormFromLink);
    });

    /* =================================================
       CONTACT REQUEST FORM
       Production: submits to the FastAPI backend via the
       same domain (Nginx proxies /api/ to port 8002).
    ================================================= */

    const contactAction = document.querySelector(".contact-action");
    const contactFormToggle = document.querySelector(
        ".contact-form-toggle"
    );
    const contactForm = document.querySelector("#contact-form");
    const contactFormClose = document.querySelector(
        ".contact-form-close"
    );
    const contactFormStatus = document.querySelector(
        ".contact-form-status"
    );

    const openContactForm = () => {
        if (!contactAction || !contactFormToggle || !contactForm) {
            return;
        }

        contactAction.classList.add("form-open");
        contactAction.closest(".contact-box")?.classList.add("form-open");
        contactFormToggle.setAttribute("aria-expanded", "true");

        window.requestAnimationFrame(() => {
            const firstField = contactForm.querySelector("input");
            if (firstField) firstField.focus({ preventScroll: true });
        });
    };

    const closeContactForm = () => {
        if (!contactAction || !contactFormToggle || !contactForm) {
            return;
        }

        contactAction.classList.remove("form-open");
        contactAction.closest(".contact-box")?.classList.remove("form-open");
        contactFormToggle.setAttribute("aria-expanded", "false");

        if (contactFormStatus) {
            contactFormStatus.textContent = "";
            contactFormStatus.style.color = "";
        }
    };

    if (contactFormToggle) {
        contactFormToggle.addEventListener("click", openContactForm);
    }

    if (contactFormClose) {
        contactFormClose.addEventListener("click", closeContactForm);
    }

    if (contactForm) {
        contactForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            if (!contactForm.checkValidity()) {
                contactForm.reportValidity();
                return;
            }

            const submitButton = contactForm.querySelector(".contact-form-submit");
            const formData = new FormData(contactForm);
            const payload = Object.fromEntries(formData.entries());

            if (contactFormStatus) {
                contactFormStatus.style.color = "#ffb28e";
                contactFormStatus.textContent = "در حال ارسال درخواست...";
            }

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.setAttribute("aria-busy", "true");
                submitButton.textContent = "لطفاً صبر کنید...";
            }

            try {
                // Relative URL → same domain (aresgroup.ir); Nginx proxies /api/ to FastAPI:8002. No CORS.
                const response = await fetch("/api/contact", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    body: JSON.stringify(payload)
                });

                const result = await response.json().catch(() => ({}));

                if (!response.ok) {
                    throw new Error(result.detail || "ارسال درخواست انجام نشد.");
                }

                contactForm.reset();

                if (contactFormStatus) {
                    contactFormStatus.style.color = "#4ade80";
                    contactFormStatus.textContent =
                        "درخواست شما با موفقیت ارسال شد. به‌زودی با شما تماس می‌گیریم.";
                }

                // Auto-close the panel after a short, readable delay.
                setTimeout(() => {
                    closeContactForm();
                }, 3200);

            } catch (error) {
                if (contactFormStatus) {
                    contactFormStatus.style.color = "#f87171";
                    contactFormStatus.textContent =
                        (error && error.message) || "خطایی رخ داد. لطفاً دوباره تلاش کنید یا تماس بگیرید.";
                }
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.removeAttribute("aria-busy");
                    submitButton.textContent = "ارسال درخواست";
                }
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && contactAction?.classList.contains("form-open")) {
            closeContactForm();
        }
    });

});

/* Empty GitHub placeholders: visible now, link can be added later. */
document.querySelectorAll(".github-placeholder").forEach((link) => {
    link.addEventListener("click", (event) => {
        event.preventDefault();
    });
});


/* Consultation links from other pages navigate to the home contact form. */
document.querySelectorAll("a.consultation-link").forEach((link) => {
    link.addEventListener("click", (event) => {
        const href = link.getAttribute("href") || "";
        if (href === "index.html#contact-form") {
            return;
        }
    });
});


/* Open the contact form automatically when arriving at #contact-form. */
if (window.location.hash === "#contact-form") {
    window.addEventListener("DOMContentLoaded", () => {
        const formToggle = document.querySelector(".contact-form-toggle");
        const contact = document.querySelector("#contact");
        if (!contact || !formToggle) return;

        // No smooth scrolling and no delayed second scroll: the panel stays put.
        window.scrollTo({
            top: contact.getBoundingClientRect().top + window.scrollY - 90,
            behavior: "auto"
        });

        if (formToggle.getAttribute("aria-expanded") !== "true") {
            formToggle.click();
        }
    });
}


/* =====================================================
   CROSS-PAGE CONSULTATION LINKS
   Service/about pages use index.html#contact-form.
   On the home page, open the existing form without moving it twice.
===================================================== */
document.addEventListener("DOMContentLoaded", () => {
    const isHomePage =
        window.location.pathname.endsWith("/") ||
        window.location.pathname.endsWith("/index.html") ||
        window.location.pathname === "";

    if (!isHomePage) return;

    document.querySelectorAll('a[href="index.html#contact-form"]').forEach((link) => {
        link.addEventListener("click", (event) => {
            const formToggle = document.querySelector(".contact-form-toggle");
            const contact = document.querySelector("#contact");
            if (!formToggle || !contact) return;

            event.preventDefault();

            window.scrollTo({
                top: contact.getBoundingClientRect().top + window.scrollY - 90,
                behavior: "auto"
            });

            if (formToggle.getAttribute("aria-expanded") !== "true") {
                formToggle.click();
            }
        });
    });
});

/* ARES services nav active indicator */
(() => {
    const servicesLink =
        document.querySelector('.navigation .services-dropdown > .nav-link') ||
        document.querySelector('.navigation .nav-services > .nav-link') ||
        document.querySelector('.navigation .services-menu > .nav-link');

    const servicesSection = document.getElementById('services');
    if (!servicesLink || !servicesSection) return;

    const setActive = () => {
        const rect = servicesSection.getBoundingClientRect();
        const active = rect.top <= 160 && rect.bottom >= 160;
        servicesLink.classList.toggle('active', active);
    };

    window.addEventListener('scroll', setActive, { passive: true });
    window.addEventListener('resize', setActive);
    setActive();
})();


/* Phone field: digits only, and yes, Persian numerals politely stay outside. */
document.addEventListener("DOMContentLoaded", () => {
    const phoneInput = document.querySelector('input[name="phone"]');
    if (!phoneInput) return;

    phoneInput.addEventListener("input", () => {
        phoneInput.value = phoneInput.value.replace(/[^0-9]/g, "").slice(0, 11);
    });
});