import sys
from pathlib import Path
from typing import Final


def get_data_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent


DATA_DIR = get_data_dir()
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
CITY_DISPLAY_NAMES: Final[dict[str, str]] = {
    "hamburg": "Hamburg",
    "vatikan": "Vatikan",
    "sylt": "Sylt",
    "malle": "Malle",
    "reloaded": "Hamburg Reloaded",
    "koeln": "Köln",
    "berlin": "Berlin",
    "muenchen": "München",
}
DEFAULT_CITY: Final[str] = "hamburg"
BASE_URL: Final[str] = CITIES[DEFAULT_CITY]
CACHE_TTL_ACTIVITIES: Final[int] = 180
CACHE_TTL_STATUS: Final[int] = 180
CACHE_TTL_LOGIN: Final[int] = 60
DB_PATH: Final[Path] = DATA_DIR / "data.db"
DB_URL: Final[str] = f"sqlite:///{DB_PATH}"
VALID_BOTTLE_DURATIONS: Final[tuple[int, ...]] = (60, 180, 360, 540, 720)
MIN_BOTTLE_PRICE_CENTS: Final[int] = 15
MAX_BOTTLE_PRICE_CENTS: Final[int] = 25
DEFAULT_BOTTLE_DURATION: Final[int] = 60
DEFAULT_BOTTLE_PAUSE: Final[int] = 1
BOTTLE_ENABLED_DEFAULT: Final[bool] = False
DEFAULT_AUTOSELL_MIN_PRICE: Final[int] = 25
AUTOSELL_ENABLED_DEFAULT: Final[bool] = False
VALID_TRAINING_SKILLS: Final[tuple[str, ...]] = ("att", "def", "agi")
DEFAULT_TRAINING_PAUSE: Final[int] = 1
DEFAULT_TRAINING_MAX_LEVEL: Final[int] = 999
TRAINING_ENABLED_DEFAULT: Final[bool] = False
AUTODRINK_ENABLED_DEFAULT: Final[bool] = False
FIGHT_ENABLED_DEFAULT: Final[bool] = False
DEFAULT_FIGHT_PAUSE: Final[int] = 1
ROTATION_ENABLED_DEFAULT: Final[bool] = False
ROTATION_DEFAULT_START: Final[str] = "bottles"
PROMILLE_WARNING_THRESHOLD: Final[float] = 3.5
PROMILLE_SAFE_TRAINING_MIN: Final[float] = 2.0
PROMILLE_SAFE_TRAINING_MAX: Final[float] = 4.0
PASSWORD_MIN_LENGTH: Final[int] = 6
USERNAME_MIN_LENGTH: Final[int] = 3
DEFAULT_USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
BOTTLE_JOB_ID: Final[str] = "bottle_collection_job"
TRAINING_JOB_ID: Final[str] = "training_task_job"
FIGHT_JOB_ID: Final[str] = "fight_task_job"
ACTIVITY_MONITOR_JOB_ID: Final[str] = "activity_monitor_job"
PAUSE_VARIATION_MIN: Final[float] = 0.99
PAUSE_VARIATION_MAX: Final[float] = 1.01
CORS_ALLOWED_ORIGINS: Final[list[str]] = ["*"]
