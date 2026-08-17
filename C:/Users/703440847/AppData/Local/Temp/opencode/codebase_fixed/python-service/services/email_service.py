"""Email notification via SendGrid / SMTP."""
import os
import ssl
import smtplib
import logging
import html as html_mod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests as req  # synchronous; kept for SendGrid (background task, not in event loop)

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
COMPANY_EMAIL    = os.getenv("COMPANY_EMAIL", "info@example.com")
SMTP_HOST        = os.getenv("SMTP_HOST", "smtp.sendgrid.net")
SMTP_PORT        = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER        = os.getenv("SMTP_USER", "apikey")
MAX_RETRIES      = 3


def _build_html_body(
    name: str, email: str, phone: Optional[str], subject: str, message: str
) -> str:
    phone_row = (
        f"<tr><td><b>Phone:</b></td><td>{html_mod.escape(phone)}</td></tr>" if phone else ""
    )
    return f"""
    <html><body style="font-family:Arial,sans-serif;">
    <h2 style="color:#161916;">New Website Enquiry</h2>
    <table>
      <tr><td><b>Name:</b></td><td>{html_mod.escape(name)}</td></tr>
      <tr><td><b>Email:</b></td><td>{html_mod.escape(email)}</td></tr>
      {phone_row}
      <tr><td><b>Subject:</b></td><td>{html_mod.escape(subject)}</td></tr>
      <tr><td><b>Message:</b></td><td><pre>{html_mod.escape(message)}</pre></td></tr>
    </table>
    <hr><p style="color:#ADB1AC;font-size:11px;">
    Submitted via the company website Contact Us form.
    </p></body></html>
    """


def send_email_notification(
    name: str, email: str, phone: Optional[str], subject: str, message: str
) -> bool:
    """Send email notification. Retries up to MAX_RETRIES times."""
    html_body     = _build_html_body(name, email, phone, subject, message)
    email_subject = f"Website Enquiry: {subject}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            ok = (
                _send_via_sendgrid(email_subject, html_body, email)
                if SENDGRID_API_KEY
                else _send_via_smtp(email_subject, html_body)
            )
            if ok:
                logger.info("Email sent successfully on attempt %d.", attempt)
                return True
        except Exception as exc:
            logger.warning("Email attempt %d failed: %s", attempt, exc)

    logger.error("All %d email delivery attempts failed.", MAX_RETRIES)
    return False


def _send_via_sendgrid(subject: str, html_body: str, reply_to: str) -> bool:
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "personalizations": [{"to": [{"email": COMPANY_EMAIL}]}],
        "from": {"email": COMPANY_EMAIL, "name": "Website Contact Form"},
        "reply_to": {"email": reply_to},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_body}],
    }
    resp = req.post(
        "https://api.sendgrid.com/v3/mail/send",
        json=payload,
        headers=headers,
        timeout=10,
    )
    return resp.status_code == 202


def _send_via_smtp(subject: str, html_body: str) -> bool:
    """
    SECURITY FIX [SEC-005]: Use an explicit ssl.create_default_context() to
    enforce certificate verification and hostname checking. Also call ehlo()
    again after STARTTLS to re-negotiate capabilities correctly.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = COMPANY_EMAIL
    msg["To"]      = COMPANY_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    ssl_ctx = ssl.create_default_context()  # enforces cert verification + hostname

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.ehlo()
        server.starttls(context=ssl_ctx)  # SEC FIX [SEC-005]: explicit secure context
        server.ehlo()                     # re-negotiate capabilities after TLS handshake
        server.login(SMTP_USER, SENDGRID_API_KEY)
        server.sendmail(COMPANY_EMAIL, COMPANY_EMAIL, msg.as_string())
    return True
