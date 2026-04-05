import re


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
PHONE_RE = re.compile(r"^\+?[0-9]{10,15}$")

ALLOWED_MEMBER_TYPES = {"Patient", "Doctor", "Staff"}
ALLOWED_ROLES = {"user", "admin"}
ALLOWED_GENDERS = {"Male", "Female", "Other"}
ALLOWED_SHIFTS = {"Morning", "Evening", "Night"}


def clean_string(value):
    return (value or "").strip()


def validate_email(value):
    return bool(EMAIL_RE.match(clean_string(value)))


def validate_username(value):
    return bool(USERNAME_RE.match(clean_string(value)))


def validate_phone(value):
    return bool(PHONE_RE.match(clean_string(value)))


def validate_password(value):
    value = value or ""
    has_letter = any(ch.isalpha() for ch in value)
    has_digit = any(ch.isdigit() for ch in value)
    return len(value) >= 8 and has_letter and has_digit


def validate_age(value):
    try:
        age = int(value)
    except (TypeError, ValueError):
        return False
    return 0 < age <= 120


def validate_non_negative_int(value):
    try:
        return int(value) >= 0
    except (TypeError, ValueError):
        return False
