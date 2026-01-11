"""
Application-wide constants and configuration.

Centralized constants for better maintainability and type safety.
"""

import sys
from pathlib import Path
from typing import Final


def get_data_dir() -> Path:
    """Get the data directory for storing database.
    
    In development mode: uses the project directory.
    In PyInstaller bundle mode: uses the directory where the exe is located.
    """
    if hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle - use exe directory
        return Path(sys.executable).parent
    else:
        # Development mode - use project directory
        return Path(__file__).parent.parent


# Get data directory
DATA_DIR = get_data_dir()

# ===========================
# API Configuration
# ===========================
# Available Pennergame cities
CITIES: Final[dict[str, str]] = {
    "hamburg": "https://www.pennergame.de",
    "vatikan": "https://vatikan.pennergame.de",
    "sylt": "https://sylt.pennergame.de",
    "malle": "https://malle.pennergame.de",
    "reloaded": "https://reloaded.pennergame.de",
    "koeln": "https://koeln.pennergame.de",
    "berlin": "https://berlin.pennergame.de",
    "muenchen": "https://muenchen.pennergame.de",
}

# Default city (Hamburg)
DEFAULT_CITY: Final[str] = "hamburg"
BASE_URL: Final[str] = CITIES[DEFAULT_CITY]

# ===========================
# Cache Configuration
# ===========================
CACHE_TTL_ACTIVITIES: Final[int] = 180  # seconds
CACHE_TTL_STATUS: Final[int] = 180  # seconds
CACHE_TTL_LOGIN: Final[int] = 60  # seconds

# ===========================
# Database Configuration
# ===========================
DB_PATH: Final[Path] = DATA_DIR / "data.db"
DB_URL: Final[str] = f"sqlite:///{DB_PATH}"

# ===========================
# Bottle Collection
# ===========================
VALID_BOTTLE_DURATIONS: Final[tuple[int, ...]] = (60, 180, 360, 540, 720)
MIN_BOTTLE_PRICE_CENTS: Final[int] = 15
MAX_BOTTLE_PRICE_CENTS: Final[int] = 25
DEFAULT_BOTTLE_DURATION: Final[int] = 60
DEFAULT_BOTTLE_PAUSE: Final[int] = 1
BOTTLE_ENABLED_DEFAULT: Final[bool] = True

# ===========================
# Auto-Sell Configuration
# ===========================
DEFAULT_AUTOSELL_MIN_PRICE: Final[int] = 25
AUTOSELL_ENABLED_DEFAULT: Final[bool] = True

# ===========================
# Training Configuration
# ===========================
VALID_TRAINING_SKILLS: Final[tuple[str, ...]] = ("att", "def", "agi")
DEFAULT_TRAINING_PAUSE: Final[int] = 1  # minutes
DEFAULT_TRAINING_MAX_LEVEL: Final[int] = 999  # No limit by default
TRAINING_ENABLED_DEFAULT: Final[bool] = True
AUTODRINK_ENABLED_DEFAULT: Final[bool] = True

# ===========================
# Promille Limits
# ===========================
PROMILLE_WARNING_THRESHOLD: Final[float] = 3.5
PROMILLE_SAFE_TRAINING_MIN: Final[float] = 2.0  # Mindest-Promille für Training
PROMILLE_SAFE_TRAINING_MAX: Final[float] = 3.0  # Maximum für sicheres Training

# ===========================
# Security
# ===========================
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


# ===========================
# Scheduler / Jobs
# ===========================
# IDs used for scheduled jobs (APScheduler job ids)
BOTTLE_JOB_ID: Final[str] = "bottle_collection_job"
TRAINING_JOB_ID: Final[str] = "training_task_job"


# ===========================
# Scheduling variations
# ===========================
# Pause variation multiplier used to add randomness to wait times
# e.g. +/-20% -> 0.8 .. 1.2
PAUSE_VARIATION_MIN: Final[float] = 0.8
PAUSE_VARIATION_MAX: Final[float] = 1.2


# ===========================
# CORS / HTTP
# ===========================
# Allowed origins for CORS middleware. Include common localhost dev ports.
CORS_ALLOWED_ORIGINS: Final[list[str]] = ["*"]