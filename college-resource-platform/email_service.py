"""
email_service.py
Handles outbound email notifications for the platform.

Currently sends two types of email:
  - Exchange request notification: when a student requests a resource, the
    uploader receives an email with the requester's name, contact details,
    and the item they want.
  - Welcome email: sent to a new user when their account is created.

Configuration (set in .env file — see .env.example):
  SMTP_HOST       SMTP server hostname  (default: smtp.gmail.com)
  SMTP_PORT       SMTP port             (default: 587  — STARTTLS)
  SMTP_USER       Sender email address  (e.g. edushare.notifications@gmail.com)
  SMTP_PASSWORD   App password for SMTP_USER
  PLATFORM_NAME   Display name in From: header (default: EduShare AI)

For Gmail, generate an App Password at:
  Google Account → Security → 2-Step Verification → App passwords
  (Your regular account password will NOT work when 2FA is enabled.)

The module degrades gracefully: if credentials are missing it returns
(False, reason) so the exchange flow still completes — only the email is skipped.
"""

import smtplib
import ssl
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import cfg

SMTP_HOST = cfg.smtp_host
SMTP_PORT = cfg.smtp_port
SMTP_USER = cfg.email_sender
SMTP_PASSWORD = cfg.email_password
PLATFORM_NAME = cfg.email_sender_name


def _is_configured() -> bool:
    return cfg.email_configured


def _send(msg: MIMEMultipart, recipient: str) -> tuple:
    """Internal helper: open SMTP connection and send msg. Returns (bool, str)."""
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, recipient, msg.as_string())
        return True, f"Email sent to {recipient}"
    except smtplib.SMTPAuthenticationError:
        return False, (
            "SMTP authentication failed. For Gmail, use an App Password "
            "(Google Account → Security → 2-Step Verification → App passwords)."
        )
    except smtplib.SMTPException as exc:
        return False, f"SMTP error: {exc}"
    except Exception as exc:
        traceback.print_exc()
        return False, f"Unexpected error sending email: {exc}"


# ---------------------------------------------------------------------------
# Exchange notification
# ---------------------------------------------------------------------------
def send_exchange_notification(
    uploader_email: str,
    uploader_name: str,
    requester_name: str,
    requester_email: str,
    item_name: str,
    category: str,
    department: str,
    estimated_value: float,
) -> tuple:
    """
    Notify the uploader that someone wants their resource.
    Returns (success: bool, message: str).
    """
    if not _is_configured():
        return False, (
            "Email notifications are not set up yet. Add EMAIL_SENDER_ADDRESS "
            "and EMAIL_SENDER_PASSWORD to your .env file to enable them."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[{PLATFORM_NAME}] Someone wants your resource: {item_name}"
    msg["From"]    = f"{PLATFORM_NAME} <{SMTP_USER}>"
    msg["To"]      = uploader_email

    plain = f"""Hi {uploader_name},

Great news! A fellow student wants to reuse your listing on {PLATFORM_NAME}.

  Resource  : {item_name}
  Category  : {category}
  Department: {department}
  Est. value: Rs.{estimated_value:.0f}

Requested by
  Name  : {requester_name}
  Email : {requester_email}

Please reach out to them at {requester_email} to arrange the handover.
Together you are helping reduce educational waste!

-- The {PLATFORM_NAME} Team
"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;background:#f4f6f8;margin:0;padding:20px}}
  .card{{background:#fff;border-radius:10px;max-width:560px;margin:0 auto;
          padding:32px;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
  h2{{color:#1a73e8;margin-top:0}}
  .badge{{display:inline-block;background:#e8f5e9;color:#2e7d32;
           padding:4px 12px;border-radius:20px;font-size:13px;margin-bottom:20px}}
  table{{width:100%;border-collapse:collapse;margin:16px 0}}
  td{{padding:8px 12px;border-bottom:1px solid #eee;font-size:14px}}
  td:first-child{{color:#666;width:130px}}
  .cta{{display:block;margin:24px 0;padding:12px 24px;background:#1a73e8;
         color:#fff!important;text-decoration:none;border-radius:6px;
         text-align:center;font-weight:bold}}
  .footer{{margin-top:24px;font-size:12px;color:#999;text-align:center}}
</style>
</head>
<body>
<div class="card">
  <h2>&#127979; {PLATFORM_NAME}</h2>
  <span class="badge">&#128230; Exchange Request</span>
  <p>Hi <strong>{uploader_name}</strong>, a student wants to reuse your listing!</p>

  <p><strong>Resource details</strong></p>
  <table>
    <tr><td>Item</td><td><strong>{item_name}</strong></td></tr>
    <tr><td>Category</td><td>{category}</td></tr>
    <tr><td>Department</td><td>{department}</td></tr>
    <tr><td>Est. value</td><td>Rs.{estimated_value:.0f}</td></tr>
  </table>

  <p><strong>Requested by</strong></p>
  <table>
    <tr><td>Name</td><td><strong>{requester_name}</strong></td></tr>
    <tr><td>Email</td><td><a href="mailto:{requester_email}">{requester_email}</a></td></tr>
  </table>

  <a href="mailto:{requester_email}?subject=Re: {item_name} on {PLATFORM_NAME}" class="cta">
    Reply to {requester_name}
  </a>

  <p style="font-size:13px;color:#555;">
    By sharing this resource you are helping reduce educational waste
    and lower costs for fellow students. Thank you! &#127807;
  </p>
  <div class="footer">{PLATFORM_NAME} &middot; Sustainable Reuse of Educational Resources</div>
</div>
</body>
</html>"""

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))
    return _send(msg, uploader_email)


# ---------------------------------------------------------------------------
# Welcome email
# ---------------------------------------------------------------------------
def send_welcome_email(user_email: str, full_name: str, username: str) -> tuple:
    """Send a welcome email to a newly registered user. Returns (bool, str)."""
    if not _is_configured():
        return False, "Email credentials not configured."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Welcome to {PLATFORM_NAME}! &#127979;"
    msg["From"]    = f"{PLATFORM_NAME} <{SMTP_USER}>"
    msg["To"]      = user_email

    plain = f"""Hi {full_name},

Welcome to {PLATFORM_NAME}! Your account is ready.

  Username : {username}
  Email    : {user_email}

You can now:
  - Browse & request reusable textbooks, calculators, lab kits, and more
  - Upload resources you no longer need
  - Get AI-powered recommendations for your department & semester
  - Track the sustainability impact of every exchange

Happy sharing!

-- The {PLATFORM_NAME} Team
"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;background:#f4f6f8;margin:0;padding:20px}}
  .card{{background:#fff;border-radius:10px;max-width:560px;margin:0 auto;
          padding:32px;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
  h2{{color:#1a73e8;margin-top:0}}
  .badge{{display:inline-block;background:#e3f2fd;color:#1565c0;
           padding:4px 12px;border-radius:20px;font-size:13px;margin-bottom:20px}}
  table{{width:100%;border-collapse:collapse;margin:16px 0}}
  td{{padding:8px 12px;border-bottom:1px solid #eee;font-size:14px}}
  td:first-child{{color:#666;width:100px}}
  ul{{padding-left:20px;line-height:1.8;color:#444}}
  .footer{{margin-top:24px;font-size:12px;color:#999;text-align:center}}
</style>
</head>
<body>
<div class="card">
  <h2>&#127979; Welcome to {PLATFORM_NAME}!</h2>
  <span class="badge">&#10003; Account Created</span>
  <p>Hi <strong>{full_name}</strong>, your account is ready.</p>
  <table>
    <tr><td>Username</td><td><strong>{username}</strong></td></tr>
    <tr><td>Email</td><td>{user_email}</td></tr>
  </table>
  <p>You can now:</p>
  <ul>
    <li>Browse &amp; request reusable textbooks, calculators, lab kits, and more</li>
    <li>Upload resources you no longer need</li>
    <li>Get AI-powered recommendations for your department &amp; semester</li>
    <li>Track the sustainability impact of every exchange</li>
  </ul>
  <p>Happy sharing! &#127807;</p>
  <div class="footer">{PLATFORM_NAME} &middot; Sustainable Reuse of Educational Resources</div>
</div>
</body>
</html>"""

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))
    return _send(msg, user_email)
