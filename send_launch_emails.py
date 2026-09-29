import os
import sys
import argparse
import smtplib
import csv
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Add backend directory to sys.path so we can import app modules
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
    load_dotenv(BACKEND_DIR / "atlas-credentials.env")
except ImportError:
    pass

from app.core.database import db

# Configuration Defaults
DEFAULT_SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
DEFAULT_SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
DEFAULT_SMTP_USER = os.getenv("SMTP_USER", "")
DEFAULT_SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
DEFAULT_FROM_NAME = os.getenv("SMTP_FROM_NAME", "de luzex Luxury Lighting")
DEFAULT_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", DEFAULT_SMTP_USER or "concierge@deluzex.com")
DEFAULT_WEBSITE_URL = os.getenv("WEBSITE_URL", "https://deluzex.com")

TEMPLATE_PATH = BACKEND_DIR / "app" / "templates" / "launch_announcement.html"

def load_template(website_url: str = DEFAULT_WEBSITE_URL, recipient_email: str = "") -> str:
    """Loads and populates the luxury launch announcement HTML template."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template not found at: {TEMPLATE_PATH}")
    
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()
        
    html = html.replace("{{ WEBSITE_URL }}", website_url)
    html = html.replace("{{ RECIPIENT_EMAIL }}", recipient_email)
    html = html.replace("{{ YEAR }}", str(datetime.now().year))
    return html

def print_banner():
    banner = """
========================================================================
             *  de luzex - VIP Launch Announcement Engine  *
                 Luxury Illumination Subscriber Notification
========================================================================
"""
    print(banner)

def get_stats():
    """Fetches and displays live subscriber statistics from MongoDB Atlas."""
    total = db.newsletter_subscribers.count_documents({})
    pending = db.newsletter_subscribers.count_documents({"is_notified": {"$ne": True}})
    notified = db.newsletter_subscribers.count_documents({"is_notified": True})
    
    print("-" * 65)
    print(f"  Total Subscribers Registered : {total}")
    print(f"  Pending Launch Notification  : {pending} (unnotified)")
    print(f"  Already Notified             : {notified}")
    print("-" * 65)
    
    recent = list(db.newsletter_subscribers.find({}).sort("subscribed_at", -1).limit(10))
    if recent:
        print(f"\nRecent 10 Subscribers:")
        print(f"{'#':<4} {'Email':<35} {'Subscribed At':<22} {'Notified':<8}")
        print("-" * 75)
        for i, sub in enumerate(recent, 1):
            sub_date = sub.get("subscribed_at")
            date_str = sub_date.strftime("%Y-%m-%d %H:%M") if isinstance(sub_date, datetime) else str(sub_date)[:16]
            is_notif = "YES" if sub.get("is_notified") else "PENDING"
            print(f"{i:<4} {sub.get('email', ''):<35} {date_str:<22} {is_notif:<8}")
        print("-" * 75)
    else:
        print("\nNo subscribers registered yet in MongoDB Atlas.")

def export_subscribers(csv_filename: str = "subscribers.csv"):
    """Exports all subscribers from MongoDB Atlas to a CSV file."""
    subscribers = list(db.newsletter_subscribers.find({}).sort("subscribed_at", -1))
    
    out_path = Path(csv_filename)
    if not out_path.is_absolute():
        out_path = BACKEND_DIR / csv_filename
        
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Email", "Subscribed At (UTC)", "Is Notified", "Notified At (UTC)", "Source"])
        for sub in subscribers:
            writer.writerow([
                str(sub.get("_id", "")),
                sub.get("email", ""),
                str(sub.get("subscribed_at", "")),
                sub.get("is_notified", False),
                str(sub.get("notified_at", "") or ""),
                sub.get("source", "coming_soon")
            ])
            
    print(f"[+] Successfully exported {len(subscribers)} subscribers to: {out_path}")

def send_email_smtp(recipient: str, subject: str, html_content: str, dry_run: bool = False):
    """Sends an individual HTML email using SMTP (SSL/TLS)."""
    if dry_run or not DEFAULT_SMTP_USER or not DEFAULT_SMTP_PASSWORD:
        if not dry_run:
            print(f"    [DRY-RUN/SIMULATION] SMTP_USER/SMTP_PASSWORD not set. Simulating delivery to: {recipient}")
        else:
            print(f"    [DRY RUN] Would send to: {recipient}")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{DEFAULT_FROM_NAME} <{DEFAULT_FROM_EMAIL}>"
    msg["To"] = recipient

    # Fallback Plaintext
    plain_text = f"We are officially live! Visit de luzex at {DEFAULT_WEBSITE_URL} and use promo code DELUZEXVIP for 10% off."
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP(DEFAULT_SMTP_HOST, DEFAULT_SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(DEFAULT_SMTP_USER, DEFAULT_SMTP_PASSWORD)
        server.send_message(msg)
        
    return True

def broadcast_launch_emails(website_url: str, dry_run: bool = False):
    """Sends launch announcement email to all pending subscribers in MongoDB Atlas."""
    pending_subs = list(db.newsletter_subscribers.find({"is_notified": {"$ne": True}}))
    total_pending = len(pending_subs)
    
    if total_pending == 0:
        print("\n[i] All registered subscribers have already been notified. Nothing to send!")
        return

    print(f"\n[!] Preparing to broadcast launch announcement to {total_pending} subscriber(s)...")
    if not DEFAULT_SMTP_USER or not DEFAULT_SMTP_PASSWORD:
        print("[!] Note: SMTP_USER or SMTP_PASSWORD is not set. Running in safe simulation mode.")
        print("    To send real emails, set SMTP_USER and SMTP_PASSWORD in atlas-credentials.env or .env.")

    success_count = 0
    failure_count = 0

    subject = "de luzex is Live — Welcome to Luxury Illumination (Your VIP Invitation)"

    for index, sub in enumerate(pending_subs, 1):
        email = sub.get("email")
        if not email:
            continue
            
        print(f"[{index}/{total_pending}] Sending launch announcement to {email}...", end=" ")
        html = load_template(website_url=website_url, recipient_email=email)
        
        try:
            send_email_smtp(email, subject, html, dry_run=dry_run)
            
            # Update MongoDB record to mark as notified
            if not dry_run:
                db.newsletter_subscribers.update_one(
                    {"_id": sub["_id"]},
                    {
                        "$set": {
                            "is_notified": True,
                            "notified_at": datetime.utcnow()
                        }
                    }
                )
            print("OK [Sent & Recorded]")
            success_count += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failure_count += 1

    print("\n" + "=" * 65)
    print(f"Broadcast Complete! Sent: {success_count} | Failed: {failure_count}")
    print("=" * 65)

def send_test_email(test_email: str, website_url: str):
    """Sends a single test email for verification."""
    print(f"\n[i] Sending 1 Test Launch Email to: {test_email}...")
    html = load_template(website_url=website_url, recipient_email=test_email)
    subject = "[TEST PREVIEW] de luzex is Live — Welcome to Luxury Illumination"
    
    try:
        send_email_smtp(test_email, subject, html)
        print(f"[+] Test email sent successfully to {test_email}!")
    except Exception as e:
        print(f"[!] Failed to send test email: {e}")
        print("\n[Tip] If using Gmail, ensure you have generated an 'App Password':")
        print("  1. Go to Google Account -> Security -> 2-Step Verification -> App Passwords.")
        print("  2. Generate a 16-character App Password.")
        print("  3. Set SMTP_USER=yourgmail@gmail.com and SMTP_PASSWORD=xxxx xxxx xxxx xxxx.")

def preview_in_browser(website_url: str):
    """Generates an HTML preview file to visually inspect the template in browser."""
    html = load_template(website_url=website_url, recipient_email="vip.client@example.com")
    preview_file = BACKEND_DIR / "preview_launch_announcement.html"
    with open(preview_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[+] Generated browser preview at: {preview_file}")
    import webbrowser
    webbrowser.open(f"file://{preview_file.resolve()}")

def main():
    print_banner()
    parser = argparse.ArgumentParser(description="de luzex - Launch Announcement Email Tool")
    parser.add_argument("--stats", action="store_true", help="Display subscriber statistics from MongoDB Atlas")
    parser.add_argument("--test", type=str, metavar="EMAIL", help="Send a test launch email to specific address")
    parser.add_argument("--broadcast", action="store_true", help="Send launch email to all pending subscribers")
    parser.add_argument("--export-csv", nargs="?", const="subscribers.csv", metavar="FILE", help="Export subscribers to CSV")
    parser.add_argument("--preview", action="store_true", help="Generate and open preview of launch email in browser")
    parser.add_argument("--dry-run", action="store_true", help="Simulate email sending without connecting to SMTP")
    parser.add_argument("--url", type=str, default=DEFAULT_WEBSITE_URL, help="Custom website store URL for CTA button")

    args = parser.parse_args()

    # Default action if no flag is provided
    if not (args.stats or args.test or args.broadcast or args.export_csv or args.preview):
        get_stats()
        print("\nAvailable Commands:")
        print("  python send_launch_emails.py --stats              # Check subscriber numbers")
        print("  python send_launch_emails.py --test user@test.com # Send 1 test email")
        print("  python send_launch_emails.py --broadcast          # Send to ALL subscribers when website goes live")
        print("  python send_launch_emails.py --export-csv         # Export all emails to CSV")
        print("  python send_launch_emails.py --preview            # Preview HTML email in browser")
        return

    if args.stats:
        get_stats()

    if args.preview:
        preview_in_browser(args.url)

    if args.test:
        send_test_email(args.test, args.url)

    if args.export_csv:
        export_subscribers(args.export_csv)

    if args.broadcast:
        broadcast_launch_emails(args.url, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
