import re
import requests
from dotenv import load_dotenv
from db_extentions import get_db_connection

load_dotenv()


def clean_email_list(emails):
    cleaned = []
    banned_domains = [
        "sentry.io",
        "wixpress.com",
        "sentry.wixpress.com",
        "sentry-next.wixpress.com",
        "oyorooms.com"
    ]

    for email in emails:
        local, _, domain = email.lower().partition("@")

        # Skip banned domains
        if domain in banned_domains:
            continue

        # Skip emails with extremely long "local" part (usually noise)
        if len(local) > 25:
            continue

        # Skip numeric-only local parts
        if local.isdigit():
            continue

        # Skip hex-like random strings
        if re.fullmatch(r"[a-f0-9]{20,}", local):
            continue

        cleaned.append(email)

    return cleaned


def extract_emails_from_website(url):
    print(f"Scraping homepage: {url}")

    # Normalize URL (remove trailing slash)
    if url.endswith("/"):
        url = url[:-1]

    all_emails = []

    # 1️⃣ Scrape homepage first
    try:
        response = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        html = response.text

        homepage_emails = re.findall(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            html
        )

        all_emails.extend(homepage_emails)

    except Exception as e:
        print("Homepage scrape error:", e)

    # Clean homepage emails
    cleaned_home = clean_email_list(list(set(all_emails)))

    # If homepage returns valid emails → return early
    if cleaned_home:
        print("Found good emails on homepage:", cleaned_home)
        return cleaned_home

    # 2️⃣ Otherwise, scrape extra pages
    EXTRA_PATHS = [
        "/contact",
        "/contact-us",
        "/contactus",
        "/about",
        "/about-us",
        "/support",
        "/help"
    ]

    for path in EXTRA_PATHS:
        full_url = url + path
        print(f"Scraping secondary page: {full_url}")

        try:
            resp = requests.get(full_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            html = resp.text

            extra_emails = re.findall(
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                html
            )

            all_emails.extend(extra_emails)

        except Exception as e:
            print(f"Error scraping {full_url}: {e}")

    # 3️⃣ Final cleaning
    cleaned_final = clean_email_list(list(set(all_emails)))
    print("Final cleaned emails:", cleaned_final)

    return cleaned_final

def update_user_credits(user_id, credits):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET credits=%s WHERE id=%s", (credits, user_id))
    conn.commit()
    cur.close()

def get_user_by_id(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, email, credits FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()

    if not row:
        return None

    return {"id": row[0], "email": row[1], "credits": row[2]}
