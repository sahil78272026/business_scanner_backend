"""
Email scraper service — extracts email addresses from business websites.
Scrapes homepage first, then falls back to common secondary pages.
"""

import re
import requests


# Domains known to produce junk emails (tracking pixels, framework noise, etc.)
BANNED_DOMAINS = [
    "sentry.io",
    "wixpress.com",
    "sentry.wixpress.com",
    "sentry-next.wixpress.com",
    "oyorooms.com",
]

# Common pages that often contain contact emails
SECONDARY_PATHS = [
    "/contact",
    "/contact-us",
    "/contactus",
    "/about",
    "/about-us",
    "/support",
    "/help",
]

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 5


def _clean_email_list(emails: list[str]) -> list[str]:
    """
    Filter out noise emails: banned domains, hex strings,
    numeric-only local parts, and overly long addresses.
    """
    cleaned = []
    for email in emails:
        local, _, domain = email.lower().partition("@")

        if domain in BANNED_DOMAINS:
            continue
        if len(local) > 25:
            continue
        if local.isdigit():
            continue
        if re.fullmatch(r"[a-f0-9]{20,}", local):
            continue

        cleaned.append(email)

    return cleaned


def _scrape_page(url: str) -> list[str]:
    """Scrape a single URL and return raw email matches."""
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
        return EMAIL_REGEX.findall(resp.text)
    except Exception:
        return []


def extract_emails_from_website(url: str) -> list[str]:
    """
    Multi-page email extraction strategy:
    1. Scrape homepage — if valid emails found, return early.
    2. Otherwise scrape secondary pages (/contact, /about, etc.)
    3. Clean and deduplicate results.
    """
    # Normalize URL
    url = url.rstrip("/")

    # Step 1: Homepage
    homepage_emails = _scrape_page(url)
    cleaned_home = _clean_email_list(list(set(homepage_emails)))

    if cleaned_home:
        return cleaned_home

    # Step 2: Secondary pages
    all_emails = []
    for path in SECONDARY_PATHS:
        page_emails = _scrape_page(url + path)
        all_emails.extend(page_emails)

    # Step 3: Clean and return
    return _clean_email_list(list(set(all_emails)))
