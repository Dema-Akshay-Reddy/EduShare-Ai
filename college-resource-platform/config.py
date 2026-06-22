"""
config.py
Loads runtime configuration from the .env file (or real environment variables
on a hosted deployment such as Streamlit Community Cloud secrets) and exposes
them as a typed namespace so the rest of the app never reads os.environ directly.

Usage:
    from config import cfg
    print(cfg.email_sender)    # -> "platform@gmail.com"
    print(cfg.email_configured)  # -> True/False
"""

import os
from pathlib import Path

# Load .env only in local development; on hosted platforms the env vars are
# already present and dotenv's load_dotenv() is a safe no-op if the file is absent.
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path, override=False)
except ImportError:
    pass  # dotenv not installed — rely on real env vars


class _Config:
    # ── Email ────────────────────────────────────────────────────────────────
    @property
    def email_sender(self) -> str:
        return os.getenv("EMAIL_SENDER_ADDRESS") or os.getenv("SMTP_USER", "")

    @property
    def email_password(self) -> str:
        return os.getenv("EMAIL_SENDER_PASSWORD") or os.getenv("SMTP_PASSWORD", "")

    @property
    def email_sender_name(self) -> str:
        return os.getenv("EMAIL_SENDER_NAME") or os.getenv("PLATFORM_NAME", "EduShare AI")

    @property
    def smtp_host(self) -> str:
        return os.getenv("EMAIL_SMTP_HOST") or os.getenv("SMTP_HOST", "smtp.gmail.com")

    @property
    def smtp_port(self) -> int:
        return int(os.getenv("EMAIL_SMTP_PORT") or os.getenv("SMTP_PORT", "587"))

    @property
    def email_configured(self) -> bool:
        """True only when real credentials have been supplied."""
        return bool(self.email_sender and self.email_password
                    and "@" in self.email_sender
                    and self.email_password not in {
                        "your_16_char_app_password",
                        "your_app_password_here",
                    })

    # ── Session ──────────────────────────────────────────────────────────────
    @property
    def session_secret(self) -> str:
        return os.getenv("SESSION_SECRET", "dev-secret-change-in-production")

    @property
    def session_ttl_days(self) -> int:
        return int(os.getenv("SESSION_TTL_DAYS", "30"))


cfg = _Config()
