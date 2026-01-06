"""
Application-wide constants and configuration.

Centralized constants for better maintainability and type safety.
"""

from typing import Final

# ===========================
# API Configuration
# ===========================
BASE_URL: Final[str] = "https://www.pennergame.de"
API_TIMEOUT: Final[int] = 30  # seconds
MAX_RETRIES: Final[int] = 3

# ===========================
# Cache Configuration
# ===========================
CACHE_TTL_ACTIVITIES: Final[int] = 180  # seconds
CACHE_TTL_STATUS: Final[int] = 180  # seconds
CACHE_TTL_LOGIN: Final[int] = 60  # seconds

# ===========================
# Database Configuration
# ===========================
DB_URL: Final[str] = "sqlite:///data.db"
LOG_RETENTION_HOURS: Final[int] = 24
LOG_CLEANUP_INTERVAL: Final[int] = 50  # Clean every N logs

# ===========================
# History Retention
# ===========================
HISTORY_RETENTION_HOURS: Final[int] = 24
MAX_HISTORY_ENTRIES: Final[int] = 1000

# ===========================
# Bottle Collection
# ===========================
VALID_BOTTLE_DURATIONS: Final[tuple[int, ...]] = (10, 30, 60, 180, 360, 540, 720)
MIN_BOTTLE_PRICE_CENTS: Final[int] = 15
MAX_BOTTLE_PRICE_CENTS: Final[int] = 25
DEFAULT_BOTTLE_DURATION: Final[int] = 60
DEFAULT_BOTTLE_PAUSE: Final[int] = 5

# ===========================
# Auto-Sell Configuration
# ===========================
DEFAULT_AUTOSELL_MIN_PRICE: Final[int] = 25
AUTOSELL_ENABLED_DEFAULT: Final[bool] = False

# ===========================
# Promille Limits
# ===========================
PROMILLE_HOSPITAL_LIMIT: Final[float] = 4.0
PROMILLE_WARNING_THRESHOLD: Final[float] = 3.5
PROMILLE_SAFE_TRAINING_MIN: Final[float] = 2.0  # Mindest-Promille für Training
PROMILLE_SAFE_TRAINING_MAX: Final[float] = 3.0  # Maximum für sicheres Training
DEFAULT_TRAINING_TARGET_PROMILLE: Final[float] = 2.5  # Optimal für Training

# ===========================
# Task Scheduling
# ===========================
SCHEDULER_MAX_INSTANCES: Final[int] = 1
SCHEDULER_COALESCE: Final[bool] = True
BOT_JOB_ID: Final[str] = "pennerbot-main-loop"
BOTTLE_JOB_ID: Final[str] = "pennerbot-bottles"
TRAINING_JOB_ID: Final[str] = "pennerbot-training"

# ===========================
# Training Configuration
# ===========================
VALID_TRAINING_SKILLS: Final[tuple[str, ...]] = ("att", "def", "agi")
DEFAULT_TRAINING_PAUSE: Final[int] = 5  # minutes
DEFAULT_TRAINING_MAX_LEVEL: Final[int] = 999  # No limit by default

# ===========================
# Random Variation (Anti-Pattern Detection)
# ===========================
PAUSE_VARIATION_MIN: Final[float] = 0.8  # -20%
PAUSE_VARIATION_MAX: Final[float] = 1.2  # +20%

# ===========================
# UI/Frontend
# ===========================
MAX_LOGS_DISPLAYED: Final[int] = 50
EVENT_HISTORY_MAX: Final[int] = 100
SSE_MAX_RECONNECT_ATTEMPTS: Final[int] = 3
SSE_KEEPALIVE_INTERVAL: Final[int] = 30  # seconds

# ===========================
# Security
# ===========================
CORS_ALLOWED_ORIGINS: Final[list[str]] = ["*"]  # TODO: Restrict in production
PASSWORD_MIN_LENGTH: Final[int] = 6
USERNAME_MIN_LENGTH: Final[int] = 3

# ===========================
# HTTP Headers
# ===========================
DEFAULT_USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)