"""Local user authentication, password policy, lockout, and UAC helpers.

Mirrors NSP 24.11 Users and Security: local users, user groups, roles,
span of control, password complexity, and brute-force lockout.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from nsp_grok.models import Access, User

PBKDF2_ROUNDS = 120_000
MAX_FAILED = 5
LOCK_MINUTES = 5

# NSP local-user default policy (Admin Guide 8.6).
PASSWORD_POLICY = {
    "min_length": 10,
    "uppercase": 1,
    "lowercase": 1,
    "digits": 1,
    "special": 1,
    "special_chars": "()?~!@#$%&*_+",
    "history": 3,
    "must_not_be_username": True,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS
    ).hex()
    return digest, salt


def verify_password(user: User, password: str) -> bool:
    digest, _ = hash_password(password, user.salt)
    return hmac.compare_digest(digest, user.password_hash)


def check_password_policy(username: str, password: str, email: str = "") -> list[str]:
    errors: list[str] = []
    p = PASSWORD_POLICY
    if len(password) < p["min_length"]:
        errors.append(f"longitud mínima: {p['min_length']} caracteres")
    if sum(c.isupper() for c in password) < p["uppercase"]:
        errors.append("se requiere al menos una mayúscula")
    if sum(c.islower() for c in password) < p["lowercase"]:
        errors.append("se requiere al menos una minúscula")
    if sum(c.isdigit() for c in password) < p["digits"]:
        errors.append("se requiere al menos un dígito")
    if sum(c in p["special_chars"] for c in password) < p["special"]:
        errors.append(f"se requiere al menos un carácter especial ({p['special_chars']})")
    if p["must_not_be_username"] and password.lower() == username.lower():
        errors.append("la contraseña no puede ser igual al usuario")
    if email and password.lower() == email.lower():
        errors.append("la contraseña no puede ser igual al correo")
    return errors


def authenticate(users: dict[str, User], username: str, password: str) -> tuple[User | None, str]:
    """Return (user, error). Usernames are case-insensitive (NSP 8.1.1)."""
    key = username.strip().lower()
    user = users.get(key)
    if user is None:
        return None, "Usuario o contraseña incorrectos."
    if user.state != "active":
        return None, "La cuenta está suspendida."
    if user.locked_until and user.locked_until > _now():
        remaining = int((user.locked_until - _now()).total_seconds() // 60) + 1
        return None, f"Cuenta bloqueada. Reintentar en {remaining} min."
    if not verify_password(user, password):
        user.failed_logins += 1
        if user.failed_logins >= MAX_FAILED:
            user.locked_until = _now() + timedelta(minutes=LOCK_MINUTES)
            return None, (
                f"Cuenta bloqueada tras {MAX_FAILED} intentos fallidos "
                f"({LOCK_MINUTES} min)."
            )
        left = MAX_FAILED - user.failed_logins
        return None, f"Usuario o contraseña incorrectos. Quedan {left} intento(s)."
    user.failed_logins = 0
    user.locked_until = None
    user.last_login = _now()
    return user, ""


def change_password(user: User, current: str, new: str) -> list[str]:
    if not verify_password(user, current):
        return ["la contraseña actual es incorrecta"]
    errors = check_password_policy(user.username, new, user.email)
    new_hash, _ = hash_password(new, user.salt)
    if new_hash in user.password_history[-PASSWORD_POLICY["history"] :]:
        errors.append(
            f"no puede repetir las últimas {PASSWORD_POLICY['history']} contraseñas"
        )
    if errors:
        return errors
    digest, salt = hash_password(new)
    user.password_history.append(user.password_hash)
    user.password_hash = digest
    user.salt = salt
    user.force_password_change = False
    return []


def can(user: User, action: Access) -> bool:
    rank = {"none": 0, "read": 1, "write": 2, "execute": 3}
    return rank[user.access] >= rank[action]


def in_span(user: User, group: str, ne_name: str = "") -> bool:
    if not user.span or user.role == "administrator":
        return True
    if group in user.span:
        return True
    return ne_name in user.span
