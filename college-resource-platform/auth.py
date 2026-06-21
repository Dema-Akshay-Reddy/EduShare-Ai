"""
auth.py
Authentication helpers for the platform's sign-up / sign-in flow.

Security approach:
- Passwords are never stored in plaintext. Each password is hashed with
  PBKDF2-HMAC-SHA256 (260,000 iterations, a NIST/OWASP-recommended modern
  iteration count) combined with a unique, randomly generated salt per user.
- Password verification uses a constant-time comparison (hmac.compare_digest)
  to avoid timing side-channel attacks.
- Login failures are rate-limited per account: after MAX_FAILED_ATTEMPTS
  consecutive failures, the account is temporarily locked for
  LOCKOUT_MINUTES to slow down brute-force/credential-stuffing attempts.
- Login error messages are intentionally generic ("Invalid username or
  password") so they don't reveal whether a username exists (prevents
  username enumeration).
- All database access uses parameterized queries (see database.py), which
  prevents SQL injection regardless of what a user types here.
"""

import hashlib
import hmac
import secrets
import re
from datetime import datetime, timedelta

PBKDF2_ITERATIONS = 260_000
SALT_BYTES = 16

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 5


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def generate_salt() -> str:
    return secrets.token_hex(SALT_BYTES)


def hash_password(password: str, salt: str = None):
    """Hash a password with PBKDF2-HMAC-SHA256. Generates a fresh random
    salt unless one is supplied (supplying one is how verification re-derives
    the hash for comparison against a stored value)."""
    if salt is None:
        salt = generate_salt()
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return derived.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    candidate_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate_hash, stored_hash)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
def validate_username(username: str):
    if not username:
        return False, "Username is required."
    if not USERNAME_PATTERN.match(username):
        return False, "Username must be 3-20 characters: letters, numbers, and underscores only."
    return True, ""


def validate_email(email: str):
    if not email:
        return False, "Email is required."
    if not EMAIL_PATTERN.match(email):
        return False, "Please enter a valid email address."
    return True, ""


def validate_password_strength(password: str):
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    return True, ""


def validate_full_name(name: str):
    if not name or not name.strip():
        return False, "Full name is required."
    if len(name.strip()) < 2:
        return False, "Please enter your full name."
    return True, ""


# ---------------------------------------------------------------------------
# Account lockout (brute-force mitigation)
# ---------------------------------------------------------------------------
def compute_lockout_until() -> str:
    return (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")


def is_locked(user: dict):
    locked_until = user.get("locked_until")
    if not locked_until:
        return False, ""
    lock_time = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S")
    if datetime.now() < lock_time:
        remaining_seconds = (lock_time - datetime.now()).total_seconds()
        remaining_minutes = max(1, int(remaining_seconds // 60) + 1)
        return True, f"Too many failed attempts. Please try again in about {remaining_minutes} minute(s)."
    return False, ""
