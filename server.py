"""FastAPI backend server for PennerBot."""

import asyncio
import atexit
import logging
import threading
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from src.cache import app_cache, cached, get_cache_stats, invalidate_cache_pattern
from src.constants import BOTTLE_JOB_ID, CORS_ALLOWED_ORIGINS, TRAINING_JOB_ID
from src.core import PennerBot
from src.db import close_db_connection, get_session
from src.error_handlers import register_error_handlers
from src.events import event_bus
from src.logging_config import get_logger, setup_logging
from src.models import Cookie, Log, Settings
from src.performance import perf_monitor
from src.query_optimizer import batch_delete_old_records, get_recent_logs_batch
from src.scheduler import scheduler, start_scheduler
from src.security import PasswordHasher
from src.validation import (
    ValidationError,
    validate_password,
    validate_user_agent,
    validate_username,
)

setup_logging(level=logging.INFO)
logger = get_logger(__name__)


# Register cleanup function to be called on exit
atexit.register(close_db_connection)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup: ensure DB is initialized (create tables + migrations)
    try:
        from src.db import init_db

        init_db()
    except Exception:
        # Best-effort - don't crash the app on migration issues
        pass

    yield
    # Shutdown: close database connection properly
    close_db_connection()


# Pydantic Models


class LoginRequest(BaseModel):
    """Login request with validation."""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)

    @field_validator("username")
    @classmethod
    def validate_username_field(cls, v: str) -> str:
        try:
            return validate_username(v)
        except ValidationError as e:
            raise ValueError(str(e))

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v: str) -> str:
        try:
            return validate_password(v)
        except ValidationError as e:
            raise ValueError(str(e))


class SettingsRequest(BaseModel):
    """Settings update request with validation."""

    user_agent: Optional[str] = Field(None, max_length=500)

    @field_validator("user_agent")
    @classmethod
    def validate_user_agent_field(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            return validate_user_agent(v)
        except ValidationError as e:
            raise ValueError(str(e))


app = FastAPI(
    title="PennerBot API",
    version="0.2.0",
    description="Automated Pennergame bot with REST API",
    lifespan=lifespan,
)

register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def performance_tracking_middleware(request: Request, call_next):
    """Track request performance."""
    endpoint = f"{request.method} {request.url.path}"

    with perf_monitor.track_request(endpoint):
        response = await call_next(request)

    return response


bot = None
_bot_lock = threading.Lock()


def get_bot() -> PennerBot:
    """Get or create the global bot instance (thread-safe singleton)."""
    global bot
    if bot is None:
        with _bot_lock:
            if bot is None:
                bot = PennerBot()
    return bot


def _get_bot() -> PennerBot:
    """Internal helper to get bot instance, alias for get_bot() for compatibility."""
    return get_bot()


def get_bot_config():
    """Hole oder erstelle Bot-Konfiguration"""
    from src.models import BotConfig

    with get_session() as s:
        config = s.query(BotConfig).first()
        if not config:
            config = BotConfig()
            s.add(config)
            s.commit()
            s.refresh(config)
        return {
            "is_running": config.is_running,
            "bottles_enabled": config.bottles_enabled,
            "bottles_duration_minutes": config.bottles_duration_minutes,
            "bottles_pause_minutes": config.bottles_pause_minutes,
            "bottles_autosell_enabled": config.bottles_autosell_enabled,
            "bottles_min_price": config.bottles_min_price,
            "training_enabled": config.training_enabled,
            "training_skills": config.training_skills,
            "training_att_max_level": config.training_att_max_level,
            "training_def_max_level": config.training_def_max_level,
            "training_agi_max_level": config.training_agi_max_level,
            "training_pause_minutes": config.training_pause_minutes,
            "training_autodrink_enabled": config.training_autodrink_enabled,
            "training_target_promille": config.training_target_promille,
            "last_started": (
                config.last_started.isoformat() if config.last_started else None
            ),
            "last_stopped": (
                config.last_stopped.isoformat() if config.last_stopped else None
            ),
        }


def update_bot_config(**kwargs):
    """Aktualisiere Bot-Konfiguration"""
    import json

    from src.models import BotConfig

    VALID_BOTTLE_DURATIONS = [60, 180, 360, 540, 720]

    if "bottles_duration_minutes" in kwargs:
        duration = kwargs["bottles_duration_minutes"]
        if duration not in VALID_BOTTLE_DURATIONS:
            duration = min(VALID_BOTTLE_DURATIONS, key=lambda x: abs(x - duration))
            kwargs["bottles_duration_minutes"] = duration
            get_bot().log(
                f"Ungültige Sammeldauer: {kwargs.get('bottles_duration_minutes')}. Nutze {duration} Minuten."
            )

    if "bottles_min_price" in kwargs:
        min_price = kwargs["bottles_min_price"]
        if min_price < 15:
            kwargs["bottles_min_price"] = 15
        elif min_price > 25:
            kwargs["bottles_min_price"] = 25

    if "training_skills" in kwargs:
        if isinstance(kwargs["training_skills"], list):
            kwargs["training_skills"] = json.dumps(kwargs["training_skills"])
        elif isinstance(kwargs["training_skills"], str):
            try:
                json.loads(kwargs["training_skills"])
            except json.JSONDecodeError:
                kwargs["training_skills"] = '["att", "def", "agi"]'

    for level_key in [
        "training_att_max_level",
        "training_def_max_level",
        "training_agi_max_level",
    ]:
        if level_key in kwargs:
            level = kwargs[level_key]
            if level < 1:
                kwargs[level_key] = 1
            elif level > 999:
                kwargs[level_key] = 999

    if "training_target_promille" in kwargs:
        from src.constants import PROMILLE_SAFE_TRAINING_MAX, PROMILLE_SAFE_TRAINING_MIN

        promille = kwargs["training_target_promille"]
        if promille < PROMILLE_SAFE_TRAINING_MIN:
            kwargs["training_target_promille"] = PROMILLE_SAFE_TRAINING_MIN
        elif promille > PROMILLE_SAFE_TRAINING_MAX:
            kwargs["training_target_promille"] = PROMILLE_SAFE_TRAINING_MAX

    with get_session() as s:
        config = s.query(BotConfig).first()
        if not config:
            config = BotConfig()
            s.add(config)

        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        s.commit()


def _bot_collect_bottles_task():
    """Task: Sammle Pfandflaschen für konfigurierte Dauer"""
    from src.models import BotConfig

    try:
        with get_session() as s:
            config = s.query(BotConfig).first()
            if not config or not config.is_running or not config.bottles_enabled:
                get_bot().log("⏭️ Bottles task skipped: bot not running or disabled")
                return

            duration_minutes = config.bottles_duration_minutes

        if not get_bot().is_logged_in(skip_log=True):
            get_bot().log("Bottles task: not logged in")
            return

        # SMART CHECK: Prüfe ob bereits Pfandflaschen sammeln läuft
        try:
            activities = get_bot().get_activities_data(use_cache=False)  # Frische Daten
            bottles_status = activities.get("bottles", {})
            if bottles_status.get("running", False):
                seconds_remaining = bottles_status.get("seconds_remaining", 0)
                if seconds_remaining > 0:
                    minutes_remaining = seconds_remaining // 60
                    get_bot().log(f"⏳ Bottle collection already running, {seconds_remaining}s remaining (~{minutes_remaining}m)")
                    # Nur neu planen, nicht neu starten
                    _schedule_next_bottles_task()
                    return
        except Exception as e:
            get_bot().log(f"Could not check bottle status: {e}, proceeding with start")

        get_bot().log(f"Starting bottle collection for {duration_minutes} minutes...")

        from src.tasks import search_bottles

        result = search_bottles(get_bot(), duration_minutes)

        if result.get("success"):
            get_bot().log(f"Bottle collection started: {result.get('message', '')}")
        else:
            get_bot().log(f"Bottle collection failed: {result.get('message', '')}")

        # Schedule next run at the end (no separate reschedule job needed)
        _schedule_next_bottles_task()

    except Exception as e:
        get_bot().log(f"Bottles task error: {e}")
        import traceback

        traceback.print_exc()


def _schedule_next_bottles_task():
    """Schedule nächste Flaschen-Sammel-Aktion nach Pause"""
    import random

    from src.models import BotConfig

    with get_session() as s:
        config = s.query(BotConfig).first()
        if not config or not config.is_running or not config.bottles_enabled:
            return

        pause_minutes = config.bottles_pause_minutes

    # Hole die ECHTE verbleibende Zeit aus dem Activity Status
    # (kann kürzer sein als konfiguriert durch Items/Konzentration)
    actual_seconds_remaining = 0
    try:
        activities = get_bot().get_activities_data(use_cache=True)
        bottles_status = activities.get("bottles", {})
        collecting = bottles_status.get("running", False)
        actual_seconds_remaining = bottles_status.get("seconds_remaining", 0)
        
        if collecting and actual_seconds_remaining > 0:
            # Task läuft noch - nur den Reschedule-Job setzen, nicht den Haupt-Job
            pass
        else:
            actual_seconds_remaining = 0
    except Exception as e:
        get_bot().log(f"Error getting bottle timer: {e}, using configured duration")
        actual_seconds_remaining = 0

    variation = random.uniform(0.8, 1.2)
    actual_pause_seconds = int(pause_minutes * 60 * variation)

    total_wait = actual_seconds_remaining + actual_pause_seconds

    actual_duration_minutes = actual_seconds_remaining // 60
    actual_pause_minutes = actual_pause_seconds // 60

    from datetime import datetime, timedelta

    run_date = datetime.now() + timedelta(seconds=total_wait)

    get_bot().log(
        f"⏰ Next bottle collection in ~{actual_duration_minutes + actual_pause_minutes} minutes "
        f"(collecting: {actual_duration_minutes}m + pause: {actual_pause_minutes}m)"
    )

    # Only schedule the main collection job - no separate reschedule job needed
    scheduler.add_job(
        _bot_collect_bottles_task,
        trigger="date",
        run_date=run_date,
        id=BOTTLE_JOB_ID,
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )


def _bot_training_task():
    """Task: Starte automatische Weiterbildungen basierend auf Konfiguration"""
    import json
    import random

    from src.models import BotConfig

    try:
        with get_session() as s:
            config = s.query(BotConfig).first()
            if not config or not config.is_running or not config.training_enabled:
                get_bot().log("⏭️ Training task skipped: bot not running or disabled")
                return

            try:
                enabled_skills = json.loads(config.training_skills)
            except Exception:
                enabled_skills = ["att", "def", "agi"]

            max_levels = {
                "att": config.training_att_max_level,
                "def": config.training_def_max_level,
                "agi": config.training_agi_max_level,
            }

            autodrink_enabled = config.training_autodrink_enabled
            target_promille = config.training_target_promille

        if not get_bot().is_logged_in(skip_log=True):
            get_bot().log("Training task: not logged in")
            return
        skills_data = get_bot().get_skills_data()
        if skills_data.get("running_skill"):
            running = skills_data["running_skill"]
            get_bot().log(
                f"⏭️ Training already running: {running.get('name', 'Unknown')} [Level {running.get('level', '?')}]"
            )
            # Schedule nächsten Check nach verbleibender Zeit
            _schedule_next_training_task()
            return

        available_skills = skills_data.get("available_skills", {})

        valid_skills = []
        for skill_type in enabled_skills:
            if skill_type in available_skills:
                current_level = available_skills[skill_type].get("level", 0)
                max_level = max_levels.get(skill_type, 999)

                if current_level < max_level:
                    valid_skills.append(skill_type)
                else:
                    get_bot().log(
                        f"⏭️ {skill_type.upper()} max level reached ({current_level}/{max_level})"
                    )

        if not valid_skills:
            get_bot().log("⏭️ No valid skills to train (all at max level)")
            _schedule_next_training_task(skip_training=True)
            return

        if autodrink_enabled:
            get_bot().log(f"Auto-Trinken aktiviert (Ziel: {target_promille:.2f}‰)")
            from src.tasks import auto_drink_before_training

            drink_result = auto_drink_before_training(get_bot(), target_promille)

            if drink_result.get("drank"):
                get_bot().log(
                    f"Auto-Trinken: {drink_result.get('message', '')} - Aktuell: {drink_result.get('current_promille', 0):.2f}‰"
                )
            else:
                get_bot().log(
                    f"ℹ️ Auto-Trinken: {drink_result.get('message', '')} - Aktuell: {drink_result.get('current_promille', 0):.2f}‰"
                )

        selected_skill = random.choice(valid_skills)

        get_bot().log(f"Starting training for: {selected_skill.upper()}...")

        from src.tasks import start_training

        result = start_training(get_bot(), selected_skill)

        if result.get("success"):
            get_bot().log(f"Training started: {result.get('message', '')}")
            
            # Nach erfolgreichem Training-Start: Ausnüchtern mit Essen
            if autodrink_enabled:
                get_bot().log("🍔 Auto-Essen aktiviert - nüchtere aus...")
                try:
                    sober_result = get_bot().sober_up_with_food(target_promille=0.0)
                    
                    if sober_result.get("ate"):
                        get_bot().log(
                            f"Auto-Essen: {sober_result.get('message', '')} - Aktuell: {sober_result.get('current_promille', 0):.2f}‰"
                        )
                    else:
                        get_bot().log(
                            f"ℹ️ Auto-Essen: {sober_result.get('message', '')} - Aktuell: {sober_result.get('current_promille', 0):.2f}‰"
                        )
                except Exception as e:
                    get_bot().log(f"Auto-Essen fehlgeschlagen: {e}")
        else:
            get_bot().log(f"Training failed: {result.get('message', '')}")

        # Schedule next run at the end (no separate reschedule job needed)
        _schedule_next_training_task(skip_training=not result.get("success", False))

    except Exception as e:
        get_bot().log(f"Training task error: {e}")
        import traceback

        traceback.print_exc()


def manage_scheduler_jobs(config):
    """
    Verwalte Scheduler-Jobs basierend auf der aktuellen Bot-Konfiguration.
    Wird aufgerufen wenn der Bot startet oder die Konfiguration geändert wird.
    """
    from datetime import datetime, timedelta

    current_bot = get_bot()
    now = datetime.now().astimezone()

    # === Pfandflaschen sammeln ===
    if config["bottles_enabled"] and config["is_running"]:
        bottle_job = scheduler.get_job(BOTTLE_JOB_ID)
        if not bottle_job:
            # Kein Job existiert - plane ersten
            current_bot.log("Plane ersten Bottle-Job...")
            run_date = now + timedelta(seconds=10)  # Sofort starten
            scheduler.add_job(
                _bot_collect_bottles_task,
                trigger="date",
                run_date=run_date,
                id=BOTTLE_JOB_ID,
                coalesce=True,
                max_instances=1,
                replace_existing=True,
            )
    else:
        # Deaktiviert oder Bot nicht running - entferne Job
        bottle_job = scheduler.get_job(BOTTLE_JOB_ID)
        if bottle_job:
            bottle_job.remove()
            current_bot.log("Bottle-Job entfernt (deaktiviert)")

    # === Weiterbildungen ===
    if config["training_enabled"] and config["is_running"]:
        training_job = scheduler.get_job(TRAINING_JOB_ID)
        if not training_job:
            # Kein Job existiert - plane ersten
            current_bot.log("Plane ersten Training-Job...")
            run_date = now + timedelta(seconds=15)
            scheduler.add_job(
                _bot_training_task,
                trigger="date",
                run_date=run_date,
                id=TRAINING_JOB_ID,
                coalesce=True,
                max_instances=1,
                replace_existing=True,
            )
            scheduler.add_job(
                _schedule_next_training_task,
                trigger="date",
                run_date=run_date + timedelta(seconds=10),
                id=f"{TRAINING_JOB_ID}-reschedule",
                coalesce=True,
                max_instances=1,
                replace_existing=True,
            )
    else:
        # Deaktiviert oder Bot nicht running - entferne Jobs
        for job_id in [TRAINING_JOB_ID, f"{TRAINING_JOB_ID}-reschedule"]:
            job = scheduler.get_job(job_id)
            if job:
                job.remove()
        if not config["training_enabled"]:
            current_bot.log("Training-Jobs entfernt (deaktiviert)")


def _schedule_next_training_task(skip_training: bool = False):
    """Schedule nächste Weiterbildungs-Aktion nach Pause"""
    import random

    from src.models import BotConfig
    from src.constants import PAUSE_VARIATION_MAX, PAUSE_VARIATION_MIN

    with get_session() as s:
        config = s.query(BotConfig).first()
        if not config or not config.is_running or not config.training_enabled:
            return

        pause_minutes = config.training_pause_minutes

    actual_seconds_remaining = 0

    if not skip_training:
        try:
            skills_data = get_bot().get_skills_data()
            running = skills_data.get("running_skill")
            if running:
                actual_seconds_remaining = running.get("seconds_remaining", 0)
                if actual_seconds_remaining > 0:
                    get_bot().log(
                        f"⏰ Training running, {actual_seconds_remaining}s remaining (~{actual_seconds_remaining // 60}m)"
                    )
        except Exception as e:
            get_bot().log(f"Could not get training timer: {e}, using pause only")
            actual_seconds_remaining = 0

    # Zufällige Variation (+/- 20%)
    variation = random.uniform(PAUSE_VARIATION_MIN, PAUSE_VARIATION_MAX)
    actual_pause_seconds = int(pause_minutes * 60 * variation)

    # Gesamtzeit
    total_wait = actual_seconds_remaining + actual_pause_seconds

    actual_duration_minutes = actual_seconds_remaining // 60
    actual_pause_minutes = actual_pause_seconds // 60

    from datetime import datetime, timedelta

    run_date = datetime.now() + timedelta(seconds=total_wait)

    if actual_seconds_remaining > 0:
        get_bot().log(
            f"⏰ Next training in ~{actual_duration_minutes + actual_pause_minutes} minutes "
            f"(training: {actual_duration_minutes}m + pause: {actual_pause_minutes}m)"
        )
    else:
        get_bot().log(f"⏰ Next training in ~{actual_pause_minutes} minutes (pause only)")

    scheduler.add_job(
        _bot_training_task,
        trigger="date",
        run_date=run_date,
        id=TRAINING_JOB_ID,
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )

    scheduler.add_job(
        _schedule_next_training_task,
        trigger="date",
        run_date=run_date + timedelta(seconds=10),
        id=f"{TRAINING_JOB_ID}-reschedule",
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )





def calculate_trend_24h(model_class, value_field: str, is_money: bool = False):
    """
    Berechne Trend der letzten 24h für ein Model

    Args:
        model_class: SQLAlchemy Model (z.B. MoneyHistory, RankHistory)
        value_field: Feldname für Wert (z.B. 'amount', 'rank', 'points')
        is_money: Wenn True, formatiere als Geld (€-Symbol, deutsche Formatierung)

    Returns:
        dict mit 'value_now', 'value_24h_ago', 'difference', 'formatted'
    """
    from datetime import datetime, timedelta

    try:
        with get_session() as s:
            # Aktueller Wert (neuester Eintrag)
            latest = s.query(model_class).order_by(model_class.id.desc()).first()
            if not latest:
                return None

            value_now = getattr(latest, value_field)

            # Wert vor 24h
            cutoff_time = datetime.now() - timedelta(hours=24)
            oldest_24h = (
                s.query(model_class)
                .filter(model_class.timestamp >= cutoff_time)
                .order_by(model_class.timestamp.asc())
                .first()
            )

            if not oldest_24h:
                # Kein Eintrag aus letzten 24h, nutze ältesten verfügbaren
                oldest_24h = (
                    s.query(model_class).order_by(model_class.timestamp.asc()).first()
                )

            if not oldest_24h or oldest_24h.id == latest.id:
                # Nur ein Eintrag, kein Trend
                return {
                    "value_now": value_now,
                    "value_24h_ago": value_now,
                    "difference": 0,
                    "formatted": "±0",
                }

            value_24h_ago = getattr(oldest_24h, value_field)
            difference = value_now - value_24h_ago

            # Formatierung
            if is_money:
                # Geld-Formatierung: €+1.234,56 (deutsches Format)
                if difference > 0:
                    formatted = (
                        f"€+{difference:,.2f}".replace(",", "X")
                        .replace(".", ",")
                        .replace("X", ".")
                    )
                elif difference < 0:
                    formatted = (
                        f"€{difference:,.2f}".replace(",", "X")
                        .replace(".", ",")
                        .replace("X", ".")
                    )
                else:
                    formatted = "€±0"
            else:
                # Integer-Formatierung: +1.234 (mit Tausender-Trennzeichen)
                if difference > 0:
                    formatted = f"+{int(difference):,}".replace(",", ".")
                elif difference < 0:
                    formatted = f"{int(difference):,}".replace(",", ".")
                else:
                    formatted = "±0"

            return {
                "value_now": value_now,
                "value_24h_ago": value_24h_ago,
                "difference": difference,
                "formatted": formatted,
            }
    except Exception as e:
        print(f"Error calculating trend: {e}")
        return None


@app.get("/api/health")
def health() -> Dict[str, Any]:
    """Health check endpoint."""
    current_bot = get_bot()
    return {
        "ok": True,
        "version": "0.2.0",
        "bot_logged_in": bool(getattr(current_bot, "logged_in", False)),
    }


@app.get("/api/metrics/performance")
def performance_metrics() -> Dict[str, Any]:
    """
    Get performance metrics (cache hit rates, request times, etc.).

    Returns:
        Performance statistics
    """
    return {
        "performance": perf_monitor.get_stats(),
        "cache": get_cache_stats(),
    }


@app.post("/api/metrics/reset")
def reset_metrics() -> Dict[str, Any]:
    """Reset performance metrics."""
    perf_monitor.reset_stats()
    return {"success": True, "message": "Metrics reset"}


@app.post("/api/cache/clear")
def clear_cache() -> Dict[str, Any]:
    """Clear application cache."""
    app_cache.clear()
    return {"success": True, "message": "Cache cleared"}


@app.post("/api/cache/invalidate")
def invalidate_cache(pattern: str) -> Dict[str, Any]:
    """
    Invalidate cache entries matching pattern.

    Args:
        pattern: Pattern to match (e.g., "dashboard", "logs")

    Returns:
        Number of invalidated entries
    """
    count = invalidate_cache_pattern(pattern)
    return {"success": True, "invalidated": count}


@app.post("/api/maintenance/cleanup")
def maintenance_cleanup() -> Dict[str, Any]:
    """
    Run maintenance cleanup (delete old logs, history).

    Returns:
        Cleanup statistics
    """
    try:
        with get_session() as s:
            deleted = batch_delete_old_records(s, hours=24)

        logger.info(f"Maintenance cleanup: {deleted['total']} records deleted")
        return {"success": True, "deleted": deleted}
    except Exception as e:
        logger.error(f"Maintenance cleanup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Server-Sent Events (SSE) für Echtzeit-Updates
# ===========================


@app.get("/api/events/stream")
async def event_stream(request: Request):
    """
    Server-Sent Events Stream für Echtzeit-Updates
    Optimized for proxy compatibility with frequent keep-alive signals.
    """
    async def event_generator():
        # Erstelle neue Queue für diesen Client
        queue = event_bus.subscribe()

        try:
            import time
            from queue import Empty

            # Sende initiales Keep-Alive mit retry-Intervall
            last_keepalive = time.time()
            yield ": keep-alive\nretry: 5000\n\n"

            while True:
                # Check ob Client noch verbunden ist
                if await request.is_disconnected():
                    break

                try:
                    # Non-blocking pop of queued event
                    event = queue.get_nowait()
                    yield event.to_sse()
                    # Reset keepalive on event
                    last_keepalive = time.time()
                    # Continue to drain any immediately available events
                    continue
                except Empty:
                    # Keine Events: sende häufiger Keep-Alive (alle 3s für Proxy-Kompatibilität)
                    now = time.time()
                    if now - last_keepalive > 3:  # 3 seconds for better proxy compatibility
                        yield ": keep-alive\nretry: 5000\n\n"
                        last_keepalive = now

                    # Kurzes Sleep um CPU-Spin zu vermeiden
                    await asyncio.sleep(0.1)

        finally:
            # Cleanup: Entferne Queue
            event_bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx buffering disable
            "Access-Control-Allow-Origin": "*",  # CORS für SSE
            "Keep-Alive": "timeout=120",  #，告诉代理保持连接
        },
    )


@app.get("/api/events/history")
def event_history(limit: int = 50) -> Dict[str, Any]:
    """Hole letzte Events (für Reconnect-Recovery)"""
    return {"events": event_bus.get_history(limit)}


# ===========================
# Optimierter Batch-Status Endpoint
# ===========================


@app.get("/api/dashboard")
@cached(ttl=5, key_prefix="dashboard")
def dashboard_status() -> Dict[str, Any]:
    """
    Optimized dashboard endpoint with 5s cache.
    Combines multiple queries for better performance.

    Returns:
        Complete dashboard state
    """
    try:
        current_bot = get_bot()
        # Aktualisiere Activity-Status mit Cache (180s)
        if getattr(current_bot, "logged_in", False):
            current_bot.refresh_status(force=False)
            perf_monitor.record_cache_hit()
        else:
            perf_monitor.record_cache_miss()

        data = current_bot.get_penner_data()
        config = get_bot_config()

        with get_session() as s:
            # Latest log (single query)
            last_log = s.query(Log).order_by(Log.id.desc()).first()
            latest_log = (
                {
                    "id": last_log.id,
                    "timestamp": last_log.timestamp.isoformat(),
                    "message": last_log.message,
                }
                if last_log
                else None
            )

            # Get city information from settings
            try:
                city_setting = s.query(Settings).filter_by(key="city").first()
                city = city_setting.value if city_setting and city_setting.value else "hamburg"
                
                # Import city mapping from constants
                from src.constants import CITIES
                
                # Map city key to display name and URL
                city_display_names = {
                    "hamburg": "Hamburg",
                    "vatikan": "Vatikan",
                    "sylt": "Sylt",
                    "malle": "Malle",
                    "reloaded": "Hamburg Reloaded",
                    "koeln": "Köln",
                    "berlin": "Berlin",
                    "muenchen": "München",
                }
                
                city_info = {
                    "name": city_display_names.get(city, "Hamburg"),
                    "url": CITIES.get(city, CITIES["hamburg"])
                }
            except Exception as e:
                logger.warning(f"Failed to get city information: {e}")
                # Fallback to default city info
                city_info = {
                    "name": "Hamburg",
                    "url": "https://www.pennergame.de"
                }

        # Format response
        penner_data = data.copy() if data else {}
        penner_data["city"] = city_info["name"]
        penner_data["city_url"] = city_info["url"]

        # Calculate trends for money, rank, and points
        if penner_data:
            from src.models import MoneyHistory, PointsHistory, RankHistory

            money_trend = calculate_trend_24h(MoneyHistory, "amount", is_money=True)
            rank_trend = calculate_trend_24h(RankHistory, "rank", is_money=False)
            points_trend = calculate_trend_24h(PointsHistory, "points", is_money=False)

            # Add formatted trends to penner_data
            if money_trend:
                penner_data["money_trend"] = money_trend["formatted"]
            if rank_trend:
                penner_data["rank_trend"] = rank_trend["formatted"]
            if points_trend:
                penner_data["points_trend"] = points_trend["formatted"]

        return {
            "logged_in": bool(getattr(current_bot, "logged_in", False)),
            "penner": penner_data,
            "activities": {
                "skill_running": getattr(current_bot, "skill_running", False),
                "skill_seconds_remaining": getattr(
                    current_bot, "skill_seconds_remaining", None
                ),
                "fight_running": getattr(current_bot, "fight_running", False),
                "fight_seconds_remaining": getattr(
                    current_bot, "fight_seconds_remaining", None
                ),
                "bottles_running": getattr(current_bot, "bottles_running", False),
                "bottles_seconds_remaining": getattr(
                    current_bot, "bottles_seconds_remaining", None
                ),
            },
            "bot": {"running": config["is_running"], "config": config},
            "latest_log": latest_log,
        }
    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _format_money_trend(difference: float) -> str:
    """Format money trend with German formatting."""
    if difference > 0:
        return (
            f"€+{difference:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    elif difference < 0:
        return (
            f"€{difference:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    return "€±0"


def _format_number_trend(difference: int) -> str:
    """Format number trend with thousand separator."""
    if difference > 0:
        return f"+{int(difference):,}".replace(",", ".")
    elif difference < 0:
        return f"{int(difference):,}".replace(",", ".")
    return "±0"


@app.get("/api/status")
@cached(ttl=10)  # Cache für 10 Sekunden
def status() -> Dict[str, Any]:
    """
    Legacy endpoint - für Rückwärtskompatibilität. Nutze /api/dashboard für bessere Performance.
    Cached für 10 Sekunden um parallele Requests zu optimieren.
    """
    try:
        current_bot = get_bot()  # Ensure bot is initialized
        
        # Aktualisiere Activity-Status mit Cache (180s) - nur wenn eingeloggt
        if getattr(current_bot, "logged_in", False):
            try:
                current_bot.refresh_status(force=False)
            except Exception as e:
                logger.warning(f"Failed to refresh status: {e}")

        # Nutze gecachte Daten statt neuem Request
        try:
            data = current_bot.get_penner_data()
        except Exception as e:
            logger.warning(f"Failed to get penner data: {e}")
            data = None
        
        # Add city information
        try:
            with get_session() as s:
                city_setting = s.query(Settings).filter_by(key="city").first()
                city = city_setting.value if city_setting and city_setting.value else "hamburg"
                
                # Import city mapping from constants
                from src.constants import CITIES
                
                # Map city key to display name and URL
                city_display_names = {
                    "hamburg": "Hamburg",
                    "vatikan": "Vatikan",
                    "sylt": "Sylt",
                    "malle": "Malle",
                    "reloaded": "Hamburg Reloaded",
                    "koeln": "Köln",
                    "berlin": "Berlin",
                    "muenchen": "München",
                }
                
                city_info = {
                    "name": city_display_names.get(city, "Hamburg"),
                    "url": CITIES.get(city, CITIES["hamburg"])
                }
                
                if data:
                    data["city"] = city_info["name"]
                    data["city_url"] = city_info["url"]
        except Exception as e:
            logger.warning(f"Failed to get city information: {e}")
            # Fallback to default city info
            if data:
                data["city"] = "Hamburg"
                data["city_url"] = "https://www.pennergame.de"

        return {
            "logged_in": bool(getattr(current_bot, "logged_in", False)),
            "penner": data,
            "activities": {
                "skill_running": getattr(current_bot, "skill_running", False),
                "skill_seconds_remaining": getattr(
                    current_bot, "skill_seconds_remaining", None
                ),
                "fight_running": getattr(current_bot, "fight_running", False),
                "fight_seconds_remaining": getattr(
                    current_bot, "fight_seconds_remaining", None
                ),
                "bottles_running": getattr(current_bot, "bottles_running", False),
                "bottles_seconds_remaining": getattr(
                    current_bot, "bottles_seconds_remaining", None
                ),
            },
        }
    except Exception as e:
        logger.error(f"Status endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/login")
def login(payload: LoginRequest) -> Dict[str, Any]:
    """
    Login endpoint with password verification and cache invalidation.

    Args:
        payload: Login credentials

    Returns:
        Success status
    """
    try:
        # 1. Check local password hash first (if configured)
        with get_session() as s:
            pw_hash = s.query(Settings).filter_by(key="password_hash").first()
            if pw_hash and pw_hash.value:
                # Local password protection enabled
                if not PasswordHasher.verify_password(payload.password, pw_hash.value):
                    logger.warning(f"Failed login attempt for user: {payload.username}")
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                logger.info("Local password verification successful")

        # 2. Proceed with Pennergame login
        current_bot = get_bot()
        success = current_bot.login(payload.username, payload.password)

        if success:
            # Save city to database if not already set (first login)
            with get_session() as s:
                city_setting = s.query(Settings).filter_by(key="city").first()
                if not city_setting:
                    # This is likely the first login, save default city
                    city_setting = Settings(key="city", value="hamburg")
                    s.add(city_setting)
                    s.commit()
                    logger.info("City saved to database on first login")

            # Invalidate all caches after login
            invalidate_cache_pattern("dashboard")
            invalidate_cache_pattern("logs")
            invalidate_cache_pattern("stats")

            # Emit Event für UI-Update
            from src.events import emit_penner_data_updated, emit_status_changed

            emit_status_changed(
                {
                    "skill_running": current_bot.skill_running,
                    "skill_seconds_remaining": getattr(current_bot, "skill_seconds_remaining", None),
                    "fight_running": current_bot.fight_running,
                    "fight_seconds_remaining": getattr(current_bot, "fight_seconds_remaining", None),
                    "bottles_running": current_bot.bottles_running,
                    "bottles_seconds_remaining": getattr(current_bot, "bottles_seconds_remaining", None),
                }
            )
            penner_data = current_bot.get_penner_data()
            if penner_data:
                emit_penner_data_updated(penner_data)

            logger.info(f"User logged in: {payload.username}")

        return {"success": bool(success)}
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/logout")
def logout() -> Dict[str, Any]:
    try:
        # Clear cookies from database
        with get_session() as s:
            s.query(Cookie).delete()
            s.commit()

        # Reset bot state
        current_bot = get_bot()
        current_bot.logged_in = False
        current_bot.cookies = {}

        # Clear bot client cookies if available
        try:
            current_bot.client.cookies.clear()
        except Exception:
            pass

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/login/auto")
def auto_login() -> Dict[str, Any]:
    """
    Auto-login endpoint that attempts to login using saved credentials.
    This is called by the frontend when the login page loads to attempt
    automatic re-login without showing the login form.

    Returns:
        Success status and login state
    """
    try:
        # Ensure bot is initialized
        current_bot = get_bot()

        # Check if already logged in
        if getattr(current_bot, "logged_in", False):
            return {
                "success": True,
                "message": "Already logged in",
                "logged_in": True
            }

        # Check if we have saved credentials first
        with get_session() as s:
            username_setting = s.query(Settings).filter_by(key="username").first()
            password_setting = s.query(Settings).filter_by(key="password_encrypted").first()

            if not username_setting or not password_setting:
                return {
                    "success": False,
                    "message": "No saved credentials",
                    "logged_in": False
                }

        # Load cookies from database before attempting login
        current_bot._load_cookies()

        # Attempt auto-relogin via the bot
        login_result = current_bot._attempt_auto_relogin()

        if login_result:
            # Invalidate caches after successful login
            invalidate_cache_pattern("dashboard")
            invalidate_cache_pattern("logs")
            invalidate_cache_pattern("stats")

            logger.info("Auto-login successful")

            return {
                "success": True,
                "message": "Auto-login successful",
                "logged_in": True
            }
        else:
            logger.warning("Auto-login failed")

            return {
                "success": False,
                "message": "Auto-login failed - please login manually",
                "logged_in": False
            }
    except Exception as e:
        logger.error(f"Auto-login error: {e}", exc_info=True)
        return {
            "success": False,
            "message": str(e),
            "logged_in": bool(getattr(get_bot(), "logged_in", False))
        }


@app.post("/api/status/refresh")
def refresh_status() -> Dict[str, Any]:
    """Erzwinge eine sofortige Aktualisierung des Status (ignoriert Cache)"""
    try:
        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        success = current_bot.refresh_status(force=True)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to refresh status")

        data = current_bot.get_penner_data()
        return {
            "success": True,
            "logged_in": bool(getattr(current_bot, "logged_in", False)),
            "penner": data,
            "activities": {
                "skill_running": getattr(current_bot, "skill_running", False),
                "skill_seconds_remaining": getattr(
                    current_bot, "skill_seconds_remaining", None
                ),
                "fight_running": getattr(current_bot, "fight_running", False),
                "fight_seconds_remaining": getattr(
                    current_bot, "fight_seconds_remaining", None
                ),
                "bottles_running": getattr(current_bot, "bottles_running", False),
                "bottles_seconds_remaining": getattr(
                    current_bot, "bottles_seconds_remaining", None
                ),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/activities/overview")
def activities_overview() -> Dict[str, Any]:
    """Gibt einen Überblick über alle laufenden Aktivitäten zurück"""
    try:
        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        return {
            "skill": {
                "running": getattr(current_bot, "skill_running", False),
                "seconds_remaining": getattr(current_bot, "skill_seconds_remaining", None),
            },
            "fight": {
                "running": getattr(current_bot, "fight_running", False),
                "seconds_remaining": getattr(current_bot, "fight_seconds_remaining", None),
            },
            "bottles": {
                "running": getattr(current_bot, "bottles_running", False),
                "seconds_remaining": getattr(current_bot, "bottles_seconds_remaining", None),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs")
def get_logs(limit: int = 50) -> Dict[str, Any]:
    """
    Get recent logs (no cache for real-time log viewing).

    Args:
        limit: Maximum number of logs to return

    Returns:
        Dictionary with logs array
    """
    try:
        with get_session() as s:
            logs = get_recent_logs_batch(s, limit)
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Failed to get logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/request_html")
def request_html() -> Dict[str, Any]:
    try:
        current_bot = get_bot()
        html = getattr(getattr(current_bot, "request", None), "text", None)
        return {"html": html or ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/database/dump")
def database_dump() -> Dict[str, Any]:
    """Return all data from all tables in the SQLite database - automatically discovers all tables."""
    try:
        from sqlalchemy import inspect

        from src.db import Base

        result = {}

        with get_session() as s:
            # Get inspector to discover all tables
            inspect(s.bind)

            # Iterate through all tables defined in Base.metadata
            for table_name, table in Base.metadata.tables.items():
                try:
                    # Query all rows from this table
                    rows = s.query(table).all()

                    # Convert rows to dictionaries
                    table_data = []
                    for row in rows:
                        row_dict = {}
                        for column in table.columns:
                            value = getattr(row, column.name, None)

                            # Format special types
                            if value is not None:
                                # DateTime to ISO string
                                if hasattr(value, "isoformat"):
                                    row_dict[column.name] = value.isoformat()
                                # Truncate long strings (e.g., cookie values)
                                elif isinstance(value, str) and len(value) > 100:
                                    row_dict[column.name] = value[:97] + "..."
                                else:
                                    row_dict[column.name] = value
                            else:
                                row_dict[column.name] = None

                        table_data.append(row_dict)

                    # Limit logs to last 100 entries
                    if table_name == "logs" and len(table_data) > 100:
                        table_data = sorted(
                            table_data, key=lambda x: x.get("id", 0), reverse=True
                        )[:100]

                    result[table_name] = table_data

                except Exception as e:
                    print(f"Error reading table {table_name}: {e}")
                    result[table_name] = []

        return {"tables": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/manual/check_login")
def manual_check_login() -> Dict[str, Any]:
    try:
        status = get_bot().is_logged_in()
        return {"logged_in": bool(status)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/manual/refresh_data")
def manual_refresh_data() -> Dict[str, Any]:
    try:
        current_bot = get_bot()
        # is_logged_in() fetched overview and updated DB already
        status = current_bot.is_logged_in()
        # get_penner_data() just reads from DB - no additional request
        data = current_bot.get_penner_data()
        return {"logged_in": bool(status), "penner": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings")
def update_settings(payload: SettingsRequest) -> Dict[str, Any]:
    try:
        current_bot = get_bot()
        with get_session() as s:
            if payload.user_agent is not None:
                # Update or create user_agent setting
                setting = s.query(Settings).filter_by(key="user_agent").first()
                if setting:
                    setting.value = payload.user_agent
                else:
                    setting = Settings(key="user_agent", value=payload.user_agent)
                    s.add(setting)
                s.commit()

                # Apply to bot
                current_bot.user_agent = payload.user_agent
                try:
                    current_bot.client.headers["User-Agent"] = payload.user_agent
                except Exception:
                    pass
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings")
def get_settings() -> Dict[str, Any]:
    try:
        with get_session() as s:
            settings_list = s.query(Settings).all()
            settings_dict = {setting.key: setting.value for setting in settings_list}

            # Don't provide a default, return None if not set
            if "user_agent" not in settings_dict:
                settings_dict["user_agent"] = None

        return {"settings": settings_dict}
    except Exception as e:
        print(f"ERROR in get_settings: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Bot API Endpoints
# ===========================


@app.get("/api/bot/config")
def get_config() -> Dict[str, Any]:
    """Hole aktuelle Bot-Konfiguration"""
    try:
        return {"config": get_bot_config()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bot/config")
def update_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Aktualisiere Bot-Konfiguration"""
    try:
        update_bot_config(**payload)
        config = get_bot_config()
        # Verwalte Scheduler-Jobs basierend auf der neuen Konfiguration
        manage_scheduler_jobs(config)
        return {"config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bot/state")
def bot_state() -> Dict[str, Any]:
    """Hole Bot-Status"""
    try:
        current_bot = get_bot()
        config = get_bot_config()
        bottle_job = scheduler.get_job(BOTTLE_JOB_ID)
        training_job = scheduler.get_job(TRAINING_JOB_ID)
        training_reschedule_job = scheduler.get_job(f"{TRAINING_JOB_ID}-reschedule")

        # Debug-Informationen
        debug_info = {
            "is_logged_in": current_bot.is_logged_in(),
            "scheduler_running": scheduler.running,
            "all_jobs": [job.id for job in scheduler.get_jobs()],
        }

        return {
            "running": config["is_running"],
            "bottle_job_scheduled": bool(bottle_job),
            "training_job_scheduled": bool(training_job),
            "training_reschedule_job_scheduled": bool(training_reschedule_job),
            "config": config,
            "debug": debug_info,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bot/start")
def bot_start() -> Dict[str, Any]:
    """Starte Bot mit aktueller Konfiguration.
    
    Der Scheduler (APScheduler) ist die EINZIGE Quelle für Timing.
    Die next_run Felder in BotConfig werden NICHT mehr benötigt.
    """
    try:
        from datetime import datetime, timedelta

        from src.events import emit_bot_state_changed

        current_bot = get_bot()
        config = get_bot_config()

        # === Scheduler starten ===
        # Jobs werden automatisch aus dem SQLAlchemy-JobStore wiederhergestellt
        start_scheduler()

        existing_jobs = scheduler.get_jobs()
        current_bot.log(f"[SCHEDULER] {len(existing_jobs)} Jobs aktiv, running={scheduler.running}")
        current_bot.log(f"[CONFIG] bottles_enabled={config['bottles_enabled']}, training_enabled={config['training_enabled']}")

        # === Update Status ===
        update_bot_config(is_running=True, last_started=datetime.now())

        # === Jobs verwalten ===
        manage_scheduler_jobs(config)
        
        current_bot.log("[RUNNING] Bot gestartet")
        current_bot.log(f"[CONFIG] bottles={config['bottles_enabled']}, training={config['training_enabled']}")

        # Emit Event für UI
        emit_bot_state_changed(True, config)

        # Login-Status prüfen
        is_logged_in = current_bot.is_logged_in(skip_log=True)
        current_bot.log(f"[LOGIN] {is_logged_in}")

        if not is_logged_in:
            current_bot.log("Nicht eingeloggt - Tasks werden bei Ausführung übersprungen")
            return {"running": True, "config": config, "warning": "Not logged in"}

        # Auto-Sell initiale Prüfung
        if config.get("bottles_autosell_enabled"):
            current_bot.log("Auto-Sell bereit")
            try:
                from src.models import BottlePrice
                with get_session() as s:
                    last_price = s.query(BottlePrice).order_by(BottlePrice.id.desc()).first()
                    if last_price:
                        current_bot._trigger_auto_sell_check(last_price.price_cents)
            except Exception as e:
                current_bot.log(f"Auto-Sell Check fehlgeschlagen: {e}")

        # Restart interrupted activities
        resume_info = current_bot.get_resume_info()
        if resume_info.get("has_interrupted_activities"):
            current_bot.log("[RESTART] Checking for interrupted activities to resume...")
            for activity in resume_info["interrupted_activities"]:
                activity_type = activity["type"]
                if activity_type == "bottles" and config["bottles_enabled"]:
                    current_bot.log("[RESTART] Restarting interrupted bottle collection...")
                    from src.tasks import search_bottles
                    duration = config["bottles_duration_minutes"]
                    result = search_bottles(current_bot, duration)
                    if result.get("success"):
                        current_bot.log(f"Restarted bottle collection: {result.get('message', '')}")
                        # Clear interrupted flag
                        from src.models import BotActivity
                        with get_session() as s:
                            interrupted = s.query(BotActivity).filter_by(activity_type="bottles", was_interrupted=True).first()
                            if interrupted:
                                interrupted.was_interrupted = False
                    else:
                        current_bot.log(f"Failed to restart bottle collection: {result.get('message', '')}")
                elif activity_type == "skill" and config["training_enabled"]:
                    subtype = activity.get("subtype")
                    if subtype:
                        current_bot.log(f"[RESTART] Restarting interrupted skill training: {subtype}")
                        result = current_bot.start_skill(subtype)
                        if result.get("success"):
                            current_bot.log(f"Restarted skill training: {result.get('message', '')}")
                            # Clear interrupted flag
                            from src.models import BotActivity
                            with get_session() as s:
                                interrupted = s.query(BotActivity).filter_by(activity_type="skill", was_interrupted=True).first()
                                if interrupted:
                                    interrupted.was_interrupted = False
                        else:
                            current_bot.log(f"Failed to restart skill training: {result.get('error', '')}")

        # Start activities that should be running but aren't
        if config["bottles_enabled"]:
            # Check if currently collecting
            try:
                activities = current_bot.get_activities_data(use_cache=False)
                bottles_status = activities.get("bottles", {})
                if not bottles_status.get("running", False):
                    current_bot.log("[START] Bottle collecting not running, starting now...")
                    from src.tasks import search_bottles
                    duration = config["bottles_duration_minutes"]
                    result = search_bottles(current_bot, duration)
                    if result.get("success"):
                        current_bot.log(f"Started bottle collection: {result.get('message', '')}")
                    else:
                        current_bot.log(f"Failed to start bottle collection: {result.get('message', '')}")
            except Exception as e:
                current_bot.log(f"Could not check/start bottle collection: {e}")

        return {"running": True, "config": get_bot_config()}
    except Exception as e:
        get_bot().log(f"Bot start error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bot/stop")
def bot_stop() -> Dict[str, Any]:
    """Stoppe Bot"""
    try:
        from datetime import datetime

        from src.events import emit_bot_state_changed

        # Update Status - Jobs werden automatisch vom Scheduler entfernt
        update_bot_config(is_running=False, last_stopped=datetime.now())

        # Entferne alle Bot-Jobs
        for job_id in [BOTTLE_JOB_ID, TRAINING_JOB_ID]:
            job = scheduler.get_job(job_id)
            if job:
                job.remove()

        get_bot().log("[STOPPED] Bot stopped")

        config = get_bot_config()

        # Emit Event für UI
        emit_bot_state_changed(False, config)

        return {"running": False, "config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Bot Actions ===


class BottleCollectRequest(BaseModel):
    time_minutes: int = 10  # 10, 30, 60, 180, 360, 540, 720


@app.post("/api/actions/bottles/collect")
def collect_bottles(payload: BottleCollectRequest) -> Dict[str, Any]:
    """Pfandflaschen sammeln starten"""
    try:
        from src.tasks import search_bottles

        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        result = search_bottles(current_bot, payload.time_minutes)
        
        if result.get("success"):
            # Invalidiere Cache
            invalidate_cache_pattern("dashboard")
            invalidate_cache_pattern("status")
            
            # Emit SSE-Events für UI-Update
            try:
                from src.events import emit_activity_started, emit_status_changed
                
                # Activity gestartet
                duration = payload.time_minutes * 60
                emit_activity_started("bottles", duration)
                
                # Sende Activity-Status
                current_bot = get_bot()
                emit_status_changed({
                    "skill_running": current_bot.skill_running,
                    "skill_seconds_remaining": getattr(current_bot, "skill_seconds_remaining", None),
                    "fight_running": current_bot.fight_running,
                    "fight_seconds_remaining": getattr(current_bot, "fight_seconds_remaining", None),
                    "bottles_running": current_bot.bottles_running,
                    "bottles_seconds_remaining": getattr(current_bot, "bottles_seconds_remaining", None),
                })
            except Exception as e:
                logger.warning(f"Failed to emit events after bottles start: {e}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/actions/bottles/status")
def bottles_status(force_refresh: bool = False) -> Dict[str, Any]:
    try:
        from src.tasks import get_bottles_status

        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        result = get_bottles_status(current_bot, force_refresh=force_refresh)

        if result.get("success"):
            bottles = result.get("bottles", {})
            return {
                "pending": bottles.get("pending", False),
                "collecting": bottles.get("collecting", False),
                "seconds_remaining": bottles.get("seconds_remaining"),
                "end_timestamp": bottles.get("end_timestamp"),
                "bottles_info": bottles,
                "overview": result.get("overview", {}),
            }
        else:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Unknown error")
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/bottles/cancel")
def cancel_bottles() -> Dict[str, Any]:
    """Pfandflaschensammeln abbrechen"""
    try:
        from src.tasks import cancel_bottle_collecting

        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        result = cancel_bottle_collecting(current_bot)
        
        if result.get("success"):
            # Invalidiere Cache
            invalidate_cache_pattern("dashboard")
            invalidate_cache_pattern("status")
            
            # Emit SSE-Events für UI-Update
            try:
                from src.events import emit_activity_completed, emit_status_changed
                
                # Activity abgebrochen
                emit_activity_completed("bottles")
                
                # Sende Activity-Status
                emit_status_changed({
                    "skill_running": bot.skill_running,
                    "skill_seconds_remaining": getattr(bot, "skill_seconds_remaining", None),
                    "fight_running": bot.fight_running,
                    "fight_seconds_remaining": getattr(bot, "fight_seconds_remaining", None),
                    "bottles_running": bot.bottles_running,
                    "bottles_seconds_remaining": getattr(bot, "bottles_seconds_remaining", None),
                })
            except Exception as e:
                logger.warning(f"Failed to emit events after bottles cancel: {e}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/bottles/sell")
def sell_bottles(payload: dict) -> Dict[str, Any]:
    """Pfandflaschen verkaufen"""
    try:
        from src.tasks import sell_bottles as sell_bottles_task

        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        amount = payload.get("amount", 1)
        result = sell_bottles_task(current_bot, amount)
        
        if result.get("success"):
            # Invalidiere Cache
            invalidate_cache_pattern("dashboard")
            invalidate_cache_pattern("status")
            
            # Emit SSE-Events für UI-Update
            try:
                from src.events import emit_money_changed
                
                # Geld hat sich geändert
                penner_data = get_bot().get_penner_data()
                if penner_data and "money_raw" in penner_data:
                    emit_money_changed(penner_data["money_raw"])
            except Exception as e:
                logger.warning(f"Failed to emit events after sell bottles: {e}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/bottles/empty-cart")
def empty_cart() -> Dict[str, Any]:
    """Einkaufswagen leeren"""
    try:
        from src.tasks import empty_bottle_cart

        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        result = empty_bottle_cart(current_bot)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/actions/bottles/inventory")
def bottles_inventory() -> Dict[str, Any]:
    """Pfandflaschen-Inventar abrufen"""
    try:
        from src.tasks import get_bottles_inventory

        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        result = get_bottles_inventory(current_bot)
        if result.get("success"):
            return result
        else:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Unknown error")
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Concentration Mode Actions ===


class ConcentrationStartRequest(BaseModel):
    mode: str = "none"  # "none", "fight", "bottles"


@app.post("/api/actions/concentration/start")
def start_concentration_mode(payload: ConcentrationStartRequest) -> Dict[str, Any]:
    """Konzentrationsmodus starten"""
    try:
        from src.tasks import start_concentration

        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        result = start_concentration(current_bot, payload.mode)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/concentration/stop")
def stop_concentration_mode() -> Dict[str, Any]:
    """Konzentrationsmodus beenden"""
    try:
        from src.tasks import stop_concentration

        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        result = stop_concentration(current_bot)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/actions/concentration/status")
def concentration_status(force_refresh: bool = False) -> Dict[str, Any]:
    try:
        from src.tasks import get_concentration_status

        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        result = get_concentration_status(current_bot, force_refresh=force_refresh)

        if result.get("success"):
            concentration = result.get("concentration", {})
            return {
                "active": concentration.get("active", False),
                "mode": concentration.get("mode", "Keine"),
                "mode_value": concentration.get("mode_value", "1"),
                "boost_percent": concentration.get("boost_percent", "0"),
                "concentration_info": concentration,
            }
        else:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Unknown error")
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Skill/Weiterbildung Actions ===


@app.get("/api/skills")
def get_skills() -> Dict[str, Any]:
    """Hole aktuelle Weiterbildungs-Informationen"""
    try:
        if not get_bot().logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        skills_data = get_bot().get_skills_data()
        return {
            "success": True,
            "running_skill": skills_data.get("running_skill"),
            "available_skills": skills_data.get("available_skills", {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SkillStartRequest(BaseModel):
    skill_type: str  # "att", "def", "agi"


@app.post("/api/skills/start")
def start_skill(payload: SkillStartRequest) -> Dict[str, Any]:
    """Starte eine Weiterbildung (Angriff, Verteidigung, Geschicklichkeit)"""
    try:
        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        if payload.skill_type not in ["att", "def", "agi"]:
            raise HTTPException(
                status_code=400, detail="Invalid skill_type. Must be att, def, or agi"
            )

        result = current_bot.start_skill(payload.skill_type)

        if result.get("success"):
            # Invalidiere Cache
            invalidate_cache_pattern("dashboard")
            invalidate_cache_pattern("status")
            
            # Emit SSE-Events für UI-Update
            try:
                from src.events import emit_activity_started, emit_status_changed
                
                # Activity gestartet
                duration = getattr(get_bot(), "skill_seconds_remaining", 0)
                emit_activity_started("skill", duration)
                
                # Sende Activity-Status
                current_bot = get_bot()
                emit_status_changed({
                    "skill_running": current_bot.skill_running,
                    "skill_seconds_remaining": getattr(current_bot, "skill_seconds_remaining", None),
                    "fight_running": current_bot.fight_running,
                    "fight_seconds_remaining": getattr(current_bot, "fight_seconds_remaining", None),
                    "bottles_running": current_bot.bottles_running,
                    "bottles_seconds_remaining": getattr(current_bot, "bottles_seconds_remaining", None),
                })
            except Exception as e:
                logger.warning(f"Failed to emit events after skill start: {e}")
            
            return result
        else:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Failed to start skill")
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/cancel")
def cancel_skill() -> Dict[str, Any]:
    """Beende die laufende Weiterbildung"""
    try:
        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        result = current_bot.cancel_skill()

        if result.get("success"):
            # Invalidiere Cache
            invalidate_cache_pattern("dashboard")
            invalidate_cache_pattern("status")
            
            # Emit SSE-Events für UI-Update
            try:
                from src.events import emit_activity_completed, emit_status_changed
                
                # Activity abgebrochen
                emit_activity_completed("skill")
                
                # Sende Activity-Status
                current_bot = get_bot()
                emit_status_changed({
                    "skill_running": current_bot.skill_running,
                    "skill_seconds_remaining": getattr(current_bot, "skill_seconds_remaining", None),
                    "fight_running": current_bot.fight_running,
                    "fight_seconds_remaining": getattr(current_bot, "fight_seconds_remaining", None),
                    "bottles_running": current_bot.bottles_running,
                    "bottles_seconds_remaining": getattr(current_bot, "bottles_seconds_remaining", None),
                })
            except Exception as e:
                logger.warning(f"Failed to emit events after skill cancel: {e}")
            
            return result
        else:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Failed to cancel skill")
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/training/status")
def training_status(force_refresh: bool = False) -> Dict[str, Any]:
    """Hole Status der automatischen Weiterbildungen"""
    try:
        from src.tasks import get_training_status

        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        result = get_training_status(current_bot, force_refresh=force_refresh)

        if result.get("success"):
            return {
                "success": True,
                "training": result.get("training"),
                "available_skills": result.get("available_skills", {}),
            }
        else:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Failed to get status")
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/drinks")
def get_drinks() -> Dict[str, Any]:
    """Hole verfügbare Getränke aus dem Inventar"""
    try:
        if not get_bot().logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        return get_bot().get_drinks_data()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DrinkRequest(BaseModel):
    item_name: str  # z.B. "Bier", "Wodka"
    item_id: str  # ID des Items
    promille: str  # Promillewert als String (z.B. "35", "250")
    amount: int = 1  # Anzahl (Standard: 1)


@app.post("/api/drinks/use")
def use_drink(payload: DrinkRequest) -> Dict[str, Any]:
    """Trinke ein Getränk aus dem Inventar"""
    try:
        if not bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        if payload.amount < 1 or payload.amount > 100:
            raise HTTPException(
                status_code=400, detail="Amount must be between 1 and 100"
            )

        result = get_bot().drink(
            item_name=payload.item_name,
            item_id=payload.item_id,
            promille=payload.promille,
            amount=payload.amount,
        )

        if result.get("success"):
            # Invalidiere Cache
            invalidate_cache_pattern("dashboard")
            invalidate_cache_pattern("status")
            
            # Emit SSE-Events für UI-Update
            try:
                from src.events import emit_promille_changed, emit_status_changed
                
                # Sende neuen Promille-Wert
                if "new_promille" in result:
                    emit_promille_changed(result["new_promille"])
                
                # Sende Activity-Status (falls sich Counter geändert haben)
                current_bot = get_bot()
                emit_status_changed({
                    "skill_running": current_bot.skill_running,
                    "skill_seconds_remaining": getattr(current_bot, "skill_seconds_remaining", None),
                    "fight_running": current_bot.fight_running,
                    "fight_seconds_remaining": getattr(current_bot, "fight_seconds_remaining", None),
                    "bottles_running": current_bot.bottles_running,
                    "bottles_seconds_remaining": getattr(current_bot, "bottles_seconds_remaining", None),
                })
            except Exception as e:
                logger.warning(f"Failed to emit events after drink: {e}")
            
            return result
        else:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Failed to drink")
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/drinks/pump")
def pump_stomach() -> Dict[str, Any]:
    """Lasse den Magen auspumpen (kostet €500.00)"""
    try:
        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        result = current_bot.pump_stomach()

        if result.get("success"):
            # Invalidiere Cache
            invalidate_cache_pattern("dashboard")
            invalidate_cache_pattern("status")
            
            # Emit SSE-Events für UI-Update
            try:
                from src.events import emit_promille_changed, emit_money_changed, emit_status_changed
                
                # Sende neuen Promille-Wert (sollte 0 sein)
                if "new_promille" in result:
                    emit_promille_changed(result["new_promille"])
                
                # Geld hat sich geändert (€500.00 bezahlt)
                penner_data = get_bot().get_penner_data()
                if penner_data and "money" in penner_data:
                    emit_money_changed(penner_data["money_raw"])
                
                # Sende Activity-Status
                current_bot = get_bot()
                emit_status_changed({
                    "skill_running": current_bot.skill_running,
                    "skill_seconds_remaining": getattr(current_bot, "skill_seconds_remaining", None),
                    "fight_running": current_bot.fight_running,
                    "fight_seconds_remaining": getattr(current_bot, "fight_seconds_remaining", None),
                    "bottles_running": current_bot.bottles_running,
                    "bottles_seconds_remaining": getattr(current_bot, "bottles_seconds_remaining", None),
                })
            except Exception as e:
                logger.warning(f"Failed to emit events after pump: {e}")
            
            return result
        else:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Failed to pump stomach")
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/food")
def get_food() -> Dict[str, Any]:
    """Hole verfügbares Essen aus dem Inventar"""
    try:
        if not get_bot().logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        return get_bot().get_food_data()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FoodRequest(BaseModel):
    item_name: str  # z.B. "Brot", "Currywurst", "Hamburger"
    item_id: str  # ID des Items
    promille: str  # Promillewert als String (z.B. "-35", "-100", "-200")
    amount: int = 1  # Anzahl (Standard: 1)


@app.post("/api/food/eat")
def eat_food(payload: FoodRequest) -> Dict[str, Any]:
    """Esse ein Essen aus dem Inventar (senkt Promille)"""
    try:
        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        if payload.amount < 1 or payload.amount > 100:
            raise HTTPException(
                status_code=400, detail="Amount must be between 1 and 100"
            )

        result = current_bot.eat_food(
            item_name=payload.item_name,
            item_id=payload.item_id,
            promille=payload.promille,
            amount=payload.amount,
        )

        if result.get("success"):
            # Invalidiere Cache
            invalidate_cache_pattern("dashboard")
            invalidate_cache_pattern("status")
            
            # Emit SSE-Events für UI-Update
            try:
                from src.events import emit_promille_changed, emit_status_changed
                
                # Sende neuen Promille-Wert
                if "new_promille" in result:
                    emit_promille_changed(result["new_promille"])
                
                # Sende Activity-Status (falls sich Counter geändert haben)
                current_bot = get_bot()
                emit_status_changed({
                    "skill_running": current_bot.skill_running,
                    "skill_seconds_remaining": getattr(current_bot, "skill_seconds_remaining", None),
                    "fight_running": current_bot.fight_running,
                    "fight_seconds_remaining": getattr(current_bot, "fight_seconds_remaining", None),
                    "bottles_running": current_bot.bottles_running,
                    "bottles_seconds_remaining": getattr(current_bot, "bottles_seconds_remaining", None),
                })
            except Exception as e:
                logger.warning(f"Failed to emit events after eating: {e}")
            
            return result
        else:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Failed to eat food")
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/food/sober")
def sober_up() -> Dict[str, Any]:
    """Automatisches Ausnüchtern durch Essen"""
    try:
        current_bot = get_bot()
        if not current_bot.logged_in:
            raise HTTPException(status_code=401, detail="Not logged in")

        result = current_bot.sober_up_with_food(target_promille=0.0)

        if result.get("success"):
            # Invalidiere Cache
            invalidate_cache_pattern("dashboard")
            invalidate_cache_pattern("status")
            
            # Emit SSE-Events für UI-Update
            try:
                from src.events import emit_promille_changed, emit_money_changed, emit_status_changed
                
                # Sende neuen Promille-Wert
                if "current_promille" in result:
                    emit_promille_changed(result["current_promille"])
                
                # Sende Activity-Status
                current_bot = get_bot()
                emit_status_changed({
                    "skill_running": current_bot.skill_running,
                    "skill_seconds_remaining": getattr(current_bot, "skill_seconds_remaining", None),
                    "fight_running": current_bot.fight_running,
                    "fight_seconds_remaining": getattr(current_bot, "fight_seconds_remaining", None),
                    "bottles_running": current_bot.bottles_running,
                    "bottles_seconds_remaining": getattr(current_bot, "bottles_seconds_remaining", None),
                })
            except Exception as e:
                logger.warning(f"Failed to emit events after sobering up: {e}")
            
            return result
        else:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Failed to sober up")
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bottle-prices")
def get_bottle_prices() -> Dict[str, Any]:
    """Hole die letzten 50 Pfandflaschenpreise für Statistik"""
    try:
        from src.db import get_session
        from src.models import BottlePrice

        with get_session() as s:
            # Hole die letzten 50 Einträge, sortiert nach ID (älteste zuerst)
            prices = s.query(BottlePrice).order_by(BottlePrice.id.asc()).limit(50).all()

            result = {
                "prices": [
                    {
                        "timestamp": price.timestamp.isoformat(),
                        "price_cents": price.price_cents,
                    }
                    for price in prices
                ],
                "count": len(prices),
                "current_price": prices[-1].price_cents if prices else None,
            }

            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/money-history")
def get_money_history() -> Dict[str, Any]:
    """Hole die letzten 50 Geldbeträge für Statistik"""
    try:
        from src.db import get_session
        from src.models import MoneyHistory

        with get_session() as s:
            # Hole die letzten 50 Einträge, sortiert nach ID (älteste zuerst)
            history = (
                s.query(MoneyHistory).order_by(MoneyHistory.id.asc()).limit(50).all()
            )

            result = {
                "history": [
                    {"timestamp": entry.timestamp.isoformat(), "amount": entry.amount}
                    for entry in history
                ],
                "count": len(history),
                "current_amount": history[-1].amount if history else None,
            }

            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/performance-stats")
def get_performance_stats():
    """Hole Performance-Statistiken vom PerformanceMonitor"""
    try:
        stats = perf_monitor.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PennerBot Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    args = parser.parse_args()
    
    uvicorn.run("server:app", host=args.host, port=args.port, reload=False)
