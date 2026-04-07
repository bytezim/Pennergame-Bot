import re
from typing import Any, Optional
from .constants import PASSWORD_MIN_LENGTH, USERNAME_MIN_LENGTH


class ValidationError(Exception):
    pass


def validate_username(username: str) -> str:
    if not username or not isinstance(username, str):
        raise ValidationError("Username is required")
    username = username.strip()
    if len(username) < USERNAME_MIN_LENGTH:
        raise ValidationError(
            f"Username must be at least {USERNAME_MIN_LENGTH} characters"
        )
    if len(username) > 50:
        raise ValidationError("Username must be less than 50 characters")
    if not re.match("^[\\w\\-]+$", username):
        raise ValidationError(
            "Username can only contain letters, numbers, underscore, and hyphen"
        )
    return username


def validate_password(password: str) -> str:
    if not password or not isinstance(password, str):
        raise ValidationError("Password is required")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValidationError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
        )
    if len(password) > 100:
        raise ValidationError("Password must be less than 100 characters")
    return password


def validate_positive_int(value: Any, name: str = "Value") -> int:
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be an integer")
    if int_value < 0:
        raise ValidationError(f"{name} must be positive")
    return int_value


def validate_user_agent(user_agent: Optional[str]) -> Optional[str]:
    if not user_agent:
        return None
    user_agent = user_agent.strip()
    if len(user_agent) < 10:
        raise ValidationError("User agent too short")
    if len(user_agent) > 500:
        raise ValidationError("User agent too long")
    return user_agent
