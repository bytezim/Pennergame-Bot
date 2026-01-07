"""Core bot functionality for Pennergame automation."""

import threading
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx

from .constants import (
    BASE_URL,
    CACHE_TTL_ACTIVITIES,
    CACHE_TTL_LOGIN,
    CACHE_TTL_STATUS,
    DEFAULT_USER_AGENT,
)
from .db import get_session
from .logging_config import get_logger
from .models import BotActivity, Cookie, Log, Penner, Plunder, Settings
from .parse import parse_header_counters, parse_overview

logger = get_logger(__name__)


class PennerBot:
    """Main bot class for Pennergame automation."""

    def __init__(self) -> None:
        logger.info("PennerBot initializing...")

        user_agent = self._load_user_agent()
        self.user_agent = user_agent

        headers = {"User-Agent": user_agent or DEFAULT_USER_AGENT}
        self.client = httpx.Client(
            follow_redirects=True,
            headers=headers,
            timeout=30.0,
        )

        self._load_cookies()
        self.request: Optional[httpx.Response] = None

        self._activities_cache: Optional[Dict[str, Any]] = None
        self._activities_cache_time: Optional[datetime] = None
        self._activities_cache_ttl = CACHE_TTL_ACTIVITIES

        self._status_cache_time: Optional[datetime] = None
        self._status_cache_ttl = CACHE_TTL_STATUS

        self.skill_running = False
        self.skill_seconds_remaining: Optional[int] = None
        self.fight_running = False
        self.fight_seconds_remaining: Optional[int] = None
        self.bottles_running = False
        self.bottles_seconds_remaining: Optional[int] = None

        self._last_login_check: Optional[datetime] = None
        self._login_status_cache = False
        self._login_cache_ttl = CACHE_TTL_LOGIN

        try:
            self.logged_in = self.is_logged_in()
        except Exception as e:
            logger.error(f"Login check failed during init: {e}", exc_info=True)
            self.logged_in = False

        try:
            self.log("[OK] Bot initialized successfully")
            
            # Restore activity states from database after successful initialization
            self.log("[SYNC] Restoring previous activity states...")
            self._load_activity_states()
            
            # Try to resume interrupted workflows
            self._restore_interrupted_workflows()
            
        except Exception as e:
            logger.error(f"DB log failed during init: {e}")

    def _load_user_agent(self) -> Optional[str]:
        try:
            with get_session() as s:
                setting = s.query(Settings).filter_by(key="user_agent").first()
                if setting and setting.value:
                    logger.info(f"Loaded user agent: {setting.value[:50]}...")
                    return setting.value
        except Exception as e:
            logger.warning(f"Failed to load user agent from settings: {e}")
        return None

    def api_get(
        self,
        client: httpx.Client,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        url = BASE_URL + endpoint
        logger.debug(f"GET {url}")
        response = client.get(url, params=params, **kwargs)
        response.raise_for_status()
        self.request = response
        return response

    def api_post(
        self,
        client: httpx.Client,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        url = BASE_URL + endpoint
        logger.debug(f"POST {url}")
        response = client.post(url, data=data, **kwargs)
        response.raise_for_status()
        self.request = response
        return response

    def is_logged_in(self, skip_log: bool = False):
        now = datetime.now()
        if self._last_login_check and self._login_status_cache:
            elapsed = (now - self._last_login_check).total_seconds()
            if elapsed < self._login_cache_ttl:
                return self._login_status_cache

        try:
            r = self.api_get(self.client, "/overview/")
            if "Profil ansehen" in r.text:
                if not skip_log and not self._login_status_cache:
                    self.log("[OK] Cookie successful")

                self._last_login_check = now
                self._login_status_cache = True

                try:
                    self.set_penner_data(r.text)
                except Exception as e:
                    self.log(f"⚠️ Failed to parse penner data: {e}")

                try:
                    counters = parse_header_counters(r.text)
                    self._update_activity_status(counters)
                except Exception as e:
                    self.log(f"[WARN] Failed to parse header counters: {e}")

                try:
                    self._save_bottle_price(r.text)
                except Exception as e:
                    self.log(f"[WARN] Failed to save bottle price: {e}")

                try:
                    self._save_money(r.text)
                except Exception as e:
                    self.log(f"[WARN] Failed to save money: {e}")

                return True

            self.log("[X] Cookie failed - attempting auto re-login")
            self._login_status_cache = False
            self._last_login_check = None
            return self._attempt_auto_relogin()
        except Exception as e:
            self.log("[X] Login check failed: " + str(e))
            self._login_status_cache = False
            self._last_login_check = None
            # Versuche Auto-Re-Login bei Fehler
            try:
                return self._attempt_auto_relogin()
            except Exception:
                return False

    def _update_activity_status(self, counters: dict):
        """
        Aktualisiert den Bot-Status basierend auf den Header-Countern

        Args:
            counters: Dict mit skill_seconds, fight_seconds, bottle_seconds
        """
        status_changed = False

        # Weiterbildung
        skill_secs = counters.get("skill_seconds")
        if skill_secs is not None and skill_secs > 0:
            if not self.skill_running:
                self.log("[INFO] Weiterbildung laeuft")
                status_changed = True
                try:
                    from .events import emit_activity_started

                    emit_activity_started("skill", skill_secs)
                except Exception:
                    pass
            self.skill_running = True
            self.skill_seconds_remaining = skill_secs
            # Detect and persist skill subtype
            skill_subtype = self._detect_skill_subtype()
            self._save_activity_state("skill", True, skill_secs, skill_subtype)
        else:
            if self.skill_running:
                self.log("[OK] Weiterbildung beendet")
                status_changed = True
                try:
                    from .events import emit_activity_completed

                    emit_activity_completed("skill")
                except Exception:
                    pass
            self.skill_running = False
            self.skill_seconds_remaining = None
            # Persist state change (subtype will be cleaned up automatically)
            self._save_activity_state("skill", False, 0)

        # Kämpfe
        fight_secs = counters.get("fight_seconds")
        if fight_secs is not None and fight_secs > 0:
            if not self.fight_running:
                self.log("[INFO] Kampf laeuft")
                status_changed = True
                try:
                    from .events import emit_activity_started

                    emit_activity_started("fight", fight_secs)
                except Exception:
                    pass
            self.fight_running = True
            self.fight_seconds_remaining = fight_secs
            # Persist state change
            self._save_activity_state("fight", True, fight_secs)
        else:
            if self.fight_running:
                self.log("[OK] Kampf beendet")
                status_changed = True
                try:
                    from .events import emit_activity_completed

                    emit_activity_completed("fight")
                except Exception:
                    pass
            self.fight_running = False
            self.fight_seconds_remaining = None
            # Persist state change
            self._save_activity_state("fight", False, 0)

        # Pfandflaschen sammeln
        bottle_secs = counters.get("bottle_seconds")
        if bottle_secs is not None and bottle_secs > 0:
            if not self.bottles_running:
                self.log("[INFO] Pfandflaschen sammeln laeuft")
                status_changed = True
                try:
                    from .events import emit_activity_started

                    emit_activity_started("bottles", bottle_secs)
                except Exception:
                    pass
            self.bottles_running = True
            self.bottles_seconds_remaining = bottle_secs
            # Persist state change
            self._save_activity_state("bottles", True, bottle_secs)
        else:
            if self.bottles_running:
                self.log("[OK] Pfandflaschen sammeln beendet")
                status_changed = True
                try:
                    from .events import emit_activity_completed

                    emit_activity_completed("bottles")
                except Exception:
                    pass
            self.bottles_running = False
            self.bottles_seconds_remaining = None
            # Persist state change
            self._save_activity_state("bottles", False, 0)

        # Emit Status-Change Event wenn sich was geändert hat
        if status_changed:
            try:
                from .events import emit_status_changed

                emit_status_changed(
                    {
                        "skill_running": self.skill_running,
                        "skill_seconds_remaining": self.skill_seconds_remaining,
                        "fight_running": self.fight_running,
                        "fight_seconds_remaining": self.fight_seconds_remaining,
                        "bottles_running": self.bottles_running,
                        "bottles_seconds_remaining": self.bottles_seconds_remaining,
                    }
                )
            except Exception:
                pass

    def _attempt_auto_relogin(self):
        """Versucht automatisch mit gespeicherten Credentials neu einzuloggen"""
        try:
            from src.security import CredentialEncryption
            
            with get_session() as s:
                username_setting = s.query(Settings).filter_by(key="username").first()
                password_setting = s.query(Settings).filter_by(key="password_encrypted").first()

                if username_setting and password_setting:
                    username = username_setting.value
                    try:
                        password = CredentialEncryption.decrypt(password_setting.value)
                    except Exception as e:
                        self.log(f"[FAIL] Failed to decrypt credentials: {e}")
                        return False

                    self.log(f"[SYNC] Auto re-login for {username}...")
                    return self.login(username, password)
                else:
                    self.log("[WARN] No saved credentials for auto re-login")
                    return False
        except Exception as e:
            self.log(f"[FAIL] Auto re-login failed: {e}")
            return False

    def refresh_status(self, force: bool = False):
        """
        Aktualisiere den Activity-Status von Pennergame

        Args:
            force: Wenn True, ignoriere Cache und hole frische Daten

        Returns:
            bool: True wenn erfolgreich aktualisiert
        """
        # Prüfe Cache-Alter
        if not force and self._status_cache_time is not None:
            age = (datetime.now() - self._status_cache_time).total_seconds()
            if age < self._status_cache_ttl:
                return True  # Cache noch gültig

        try:
            r = self.api_get(self.client, "/overview/")
            counters = parse_header_counters(r.text)
            self._update_activity_status(counters)
            self._status_cache_time = datetime.now()

            # Aktualisiere auch Penner-Daten
            try:
                self.set_penner_data(r.text)
            except Exception as e:
                self.log(f"[WARN] Failed to parse penner data: {e}")

            # Speichere Bottle-Preis (nur bei Änderung)
            try:
                self._save_bottle_price(r.text)
            except Exception as e:
                self.log(f"[WARN] Failed to save bottle price: {e}")

            # Speichere Geldbetrag (nur bei Änderung)
            try:
                self._save_money(r.text)
            except Exception as e:
                self.log(f"[WARN] Failed to save money: {e}")

            return True
        except Exception as e:
            self.log(f"[FAIL] Failed to refresh status: {e}")
            return False

    def _trigger_auto_sell_check(self, current_price_cents: int):
        """
        Prüfe ob Auto-Sell aktiviert ist und führe bei Erfüllung direkt aus.
        Wird aufgerufen wenn sich der Bottle Price ändert.
        """
        from .models import BotConfig

        # Hole Config
        with get_session() as s:
            config = s.query(BotConfig).first()
            if not config:
                self.log("[WARN] Auto-Sell: Keine Bot-Config gefunden")
                return

            if not config.is_running:
                self.log("[WARN] Auto-Sell: Bot laeuft nicht (is_running=False)")
                return

            if not config.bottles_autosell_enabled:
                self.log("[WARN] Auto-Sell: Feature ist deaktiviert")
                return

            min_price = config.bottles_min_price
            self.log(
                f"[SEARCH] Auto-Sell Check: Aktuell {current_price_cents} Cent, Schwelle {min_price} Cent"
            )

        # Prüfe Preis-Bedingung
        if current_price_cents < min_price:
            self.log(
                f"[SKIP] Auto-Sell: Preis zu niedrig ({current_price_cents} Cent < {min_price} Cent)"
            )
            return

        # Prüfe ob Flaschen vorhanden - hole von /stock/bottle/
        try:
            from .parse import parse_bottle_count

            response = self.api_get(self.client, "/stock/bottle/")
            bottle_count = parse_bottle_count(response.text)

        except Exception as e:
            self.log(f"[WARN] Auto-Sell: Fehler beim Laden der Flaschen-Daten: {e}")
            return

        self.log(f"[SEARCH] Auto-Sell: {bottle_count} Flaschen verfuegbar")

        if bottle_count <= 0:
            self.log("[SKIP] Auto-Sell: Keine Flaschen zum Verkaufen")
            return

        # Bedingungen erfuellt! Fuehre Auto-Sell aus
        self.log(
            f"[TRIGGER] Auto-Sell Trigger: {bottle_count} Flaschen @ {current_price_cents} Cent (Schwelle: {min_price} Cent)"
        )

        # Führe Verkauf direkt aus (nicht über Scheduler)
        try:
            from .tasks import sell_bottles

            result = sell_bottles(self, bottle_count)

            if result.get("success"):
                self.log(f"[OK] Auto-Sell: EUR {result.get('earned', '0')} erwirtschaftet")
            else:
                self.log(f"[FAIL] Auto-Sell fehlgeschlagen: {result.get('message')}")
        except Exception as e:
            self.log(f"[FAIL] Auto-Sell Fehler: {e}")

    def _save_bottle_price(self, html: str):
        """
        Speichere den aktuellen Pfandflaschenpreis in der Datenbank.
        Speichert nur, wenn sich der Preis geändert hat.
        Hält Einträge der letzten 24 Stunden.
        """
        from datetime import timedelta

        from .models import BottlePrice
        from .parse import parse_bottle_price

        current_price = parse_bottle_price(html)
        if current_price == 0:
            return  # Kein gültiger Preis gefunden

        try:
            with get_session() as s:
                # Hole letzten Eintrag
                last_entry = s.query(BottlePrice).order_by(BottlePrice.id.desc()).first()

                # Speichere nur wenn Preis sich geändert hat
                if last_entry is None or last_entry.price_cents != current_price:
                    # Prüfe ob letzter Eintrag sehr recent ist (< 2s) mit gleichem Wert
                    # um doppelte Logs durch parallele Requests zu vermeiden
                    if last_entry and last_entry.price_cents == current_price:
                        time_since_last = (
                            datetime.now() - last_entry.timestamp
                        ).total_seconds()
                        if time_since_last < 2:
                            return  # Skip - bereits geloggt

                    new_entry = BottlePrice(price_cents=current_price)
                    s.add(new_entry)
                    # Context manager committed automatisch

            # Cleanup in separater Session
            with get_session() as s:
                cutoff_time = datetime.now() - timedelta(hours=24)
                old_entries = (
                    s.query(BottlePrice)
                    .filter(BottlePrice.timestamp < cutoff_time)
                    .all()
                )
                if old_entries:
                    for entry in old_entries:
                        s.delete(entry)
                    # Context manager committed automatisch

            self.log(f"[MONEY] Bottle price changed: {current_price} Cent")

            # Emit Event
            try:
                from .events import emit_bottle_price_changed

                emit_bottle_price_changed(current_price)
            except Exception:
                pass

            # Trigger Auto-Sell Check bei Preis-Änderung
            try:
                self._trigger_auto_sell_check(current_price)
            except Exception as e:
                self.log(f"[WARN] Auto-Sell check error: {e}")
        except Exception as e:
            if "locked" not in str(e).lower():
                self.log(f"[WARN] Failed to save bottle price: {e}")

    def _save_money(self, html: str):
        """
        Speichere den aktuellen Geldbetrag in der Datenbank.
        Speichert nur, wenn sich der Betrag geändert hat.
        Hält Einträge der letzten 24 Stunden.
        """
        from datetime import timedelta

        from .models import MoneyHistory
        from .parse import parse_money

        current_money = parse_money(html)
        if current_money == 0.0:
            return  # Kein gültiger Betrag gefunden

        try:
            with get_session() as s:
                # Hole letzten Eintrag
                last_entry = s.query(MoneyHistory).order_by(MoneyHistory.id.desc()).first()

                # Speichere nur wenn Betrag sich geändert hat
                # Verwende Toleranz von 0.01€ um Rundungsfehler zu vermeiden
                if last_entry is None or abs(last_entry.amount - current_money) > 0.01:
                    # Prüfe ob letzter Eintrag sehr recent ist (< 2s) mit gleichem Wert
                    # um doppelte Logs durch parallele Requests zu vermeiden
                    if last_entry and abs(last_entry.amount - current_money) <= 0.01:
                        time_since_last = (
                            datetime.now() - last_entry.timestamp
                        ).total_seconds()
                        if time_since_last < 2:
                            return  # Skip - bereits geloggt

                    new_entry = MoneyHistory(amount=current_money)
                    s.add(new_entry)
                    # WICHTIG: Kein s.commit() hier - der context manager macht das automatisch!

                    # Lösche Einträge älter als 24 Stunden IN SEPARATER SESSION
                    # um "transaction in progress" Fehler zu vermeiden
            
            # Cleanup in separater Session
            with get_session() as s:
                cutoff_time = datetime.now() - timedelta(hours=24)
                old_entries = (
                    s.query(MoneyHistory)
                    .filter(MoneyHistory.timestamp < cutoff_time)
                    .all()
                )
                if old_entries:
                    for entry in old_entries:
                        s.delete(entry)
                    # Context manager committed automatisch

            self.log(f"[MONEY] Money changed: EUR {current_money:,.2f}")

            # Emit Event
            try:
                from .events import emit_money_changed

                emit_money_changed(current_money)
            except Exception:
                pass
        except Exception as e:
            # Vermeide Logging wenn DB locked
            if "locked" not in str(e).lower():
                self.log(f"[WARN] Failed to save money: {e}")

    def _save_rank(self, rank: int):
        """
        Speichere den aktuellen Rang in der Datenbank.
        Speichert nur, wenn sich der Rang geändert hat.
        Hält Einträge der letzten 24 Stunden.
        """
        from datetime import timedelta

        from .models import RankHistory

        if rank <= 0:
            return  # Ungültiger Rang

        try:
            with get_session() as s:
                # Hole letzten Eintrag
                last_entry = s.query(RankHistory).order_by(RankHistory.id.desc()).first()

                # Speichere nur wenn Rang sich geändert hat
                if last_entry is None or last_entry.rank != rank:
                    # Prüfe ob letzter Eintrag sehr recent ist (< 2s) mit gleichem Wert
                    if last_entry and last_entry.rank == rank:
                        time_since_last = (
                            datetime.now() - last_entry.timestamp
                        ).total_seconds()
                        if time_since_last < 2:
                            return  # Skip - bereits geloggt

                    new_entry = RankHistory(rank=rank)
                    s.add(new_entry)
                    # Context manager committed automatisch

            # Cleanup in separater Session
            with get_session() as s:
                cutoff_time = datetime.now() - timedelta(hours=24)
                old_entries = (
                    s.query(RankHistory)
                    .filter(RankHistory.timestamp < cutoff_time)
                    .all()
                )
                if old_entries:
                    for entry in old_entries:
                        s.delete(entry)
                    # Context manager committed automatisch

            self.log(f"[RANK] Rank changed: {rank}")
        except Exception as e:
            if "locked" not in str(e).lower():
                self.log(f"[WARN] Failed to save rank: {e}")

    def _save_points(self, points: int):
        """
        Speichere die aktuellen Punkte in der Datenbank.
        Speichert nur, wenn sich die Punkte geändert haben.
        Hält Einträge der letzten 24 Stunden.
        """
        from datetime import timedelta

        from .models import PointsHistory

        if points < 0:
            return  # Ungültige Punkte

        try:
            with get_session() as s:
                # Hole letzten Eintrag
                last_entry = (
                    s.query(PointsHistory).order_by(PointsHistory.id.desc()).first()
                )

                # Speichere nur wenn Punkte sich geändert haben
                if last_entry is None or last_entry.points != points:
                    # Prüfe ob letzter Eintrag sehr recent ist (< 2s) mit gleichem Wert
                    if last_entry and last_entry.points == points:
                        time_since_last = (
                            datetime.now() - last_entry.timestamp
                        ).total_seconds()
                        if time_since_last < 2:
                            return  # Skip - bereits geloggt

                    new_entry = PointsHistory(points=points)
                    s.add(new_entry)
                    # Context manager committed automatisch

            # Cleanup in separater Session
            with get_session() as s:
                cutoff_time = datetime.now() - timedelta(hours=24)
                old_entries = (
                    s.query(PointsHistory)
                    .filter(PointsHistory.timestamp < cutoff_time)
                    .all()
                )
                if old_entries:
                    for entry in old_entries:
                        s.delete(entry)
                    # Context manager committed automatisch

            self.log(f"[PTS] Points changed: {points:,}")
        except Exception as e:
            if "locked" not in str(e).lower():
                self.log(f"[WARN] Failed to save points: {e}")

    def _save_cookies(self):
        try:
            # Handle httpx cookies safely - they might be strings or objects
            cookies_dict = {}
            try:
                # Try to iterate as httpx.Cookies object
                for cookie in self.client.cookies:
                    if hasattr(cookie, 'name') and hasattr(cookie, 'value'):
                        cookies_dict[cookie.name] = cookie.value
                    elif isinstance(cookie, tuple):
                        # Sometimes cookies come as (name, value) tuples
                        cookies_dict[cookie[0]] = cookie[1]
            except Exception:
                # Fallback: use the cookies jar directly
                try:
                    cookies_dict = dict(self.client.cookies)
                except Exception:
                    pass
            
            if not cookies_dict:
                return  # No cookies to save
            
            with get_session() as s:
                s.query(Cookie).delete()
                for k, v in cookies_dict.items():
                    # Ensure value is a string
                    if isinstance(v, str):
                        s.add(Cookie(name=k, value=v))
                s.commit()
        except Exception as e:
            self.log(f"[WARN] Failed to save cookies: {e}")

    def _load_cookies(self):
        with get_session() as s:
            cookies = s.query(Cookie).all()
            for cookie in cookies:
                self.client.cookies.set(cookie.name, cookie.value)

    def log(self, msg: str):
        """
        Log a message: store in DB and emit to UI (console output skipped for Windows compatibility).
        """
        # Store in DB and emit to UI - skip console output entirely to avoid encoding issues
        def _db_log():
            try:
                from datetime import timedelta
                
                with get_session() as s:
                    log_entry = Log(message=msg, timestamp=datetime.now())
                    s.add(log_entry)
                    s.commit()

                    # Delete logs older than 24 hours (every 50 logs)
                    log_count = s.query(Log).count()
                    if log_count % 50 == 0:
                        cutoff_time = datetime.now() - timedelta(hours=24)
                        old_logs = s.query(Log).filter(Log.timestamp < cutoff_time).all()
                        for old_log in old_logs:
                            s.delete(old_log)
                        if old_logs:
                            s.commit()
            except Exception:
                pass  # Silent fail
        
        # Emit Event for UI
        def _emit_event():
            try:
                from .events import emit_log_added
                emit_log_added(msg)
            except Exception:
                pass
        
        # Run both in background threads - fire and forget
        threading.Thread(target=_db_log, daemon=True).start()
        threading.Thread(target=_emit_event, daemon=True).start()

    def login(self, username: str, password: str):
        try:
            # Direkt login - kein vorheriger GET auf / notwendig
            self.log("[INFO] Logging in as " + username)
            self.request = self.api_post(
                self.client,
                "/login/check/",
                data={
                    "username": username,
                    "password": password,
                    "submitForm": "Login",
                },
            )

            success_indicators = [
                "Profil ansehen" in self.request.text,
                "/overview/" in self.request.text,
                "Mein Penner" in self.request.text,
                self.request.status_code == 200
                and "login" not in str(self.request.url).lower(),
            ]

            if any(success_indicators):
                self.logged_in = True
                self.log("[OK] Login successful")
                self._save_cookies()

                # Save credentials ENCRYPTED
                from src.security import CredentialEncryption
                
                with get_session() as s:
                    s.query(Settings).filter_by(key="username").delete()
                    s.query(Settings).filter_by(key="password_encrypted").delete()
                    s.add(Settings(key="username", value=username))
                    s.add(Settings(key="password_encrypted", value=CredentialEncryption.encrypt(password)))
                    # Context manager commits automatically

                # Restore interrupted workflows after successful login
                self._restore_interrupted_workflows()

                try:
                    self.set_penner_data(self.request.text)
                except Exception as e:
                    self.log(f"⚠️ Failed to parse penner data: {e}")
                return True
            else:
                self.log("[FAIL] Login failed")
                return False
        except Exception as e:
            self.log(f"[FAIL] Login error: {e}")
            raise

    def set_penner_data(self, r: str):
        penner_data = parse_overview(r)
        with get_session() as s:
            penner = s.query(Penner).filter_by(user_id=penner_data["user_id"]).first()
            if not penner:
                penner = Penner(
                    **{k: v for k, v in penner_data.items() if k != "plunder"}
                )
                s.add(penner)
            else:
                for k, v in penner_data.items():
                    if k != "plunder":
                        setattr(penner, k, v)
            s.commit()
            s.query(Plunder).filter_by(penner_id=penner.id).delete()
            for pl in penner_data.get("plunder", []):
                s.add(Plunder(penner_id=penner.id, slot=pl["slot"], name=pl["name"]))
            s.commit()

        # Speichere Rang und Punkte in Historie
        try:
            if "rank" in penner_data and penner_data["rank"]:
                self._save_rank(penner_data["rank"])
        except Exception as e:
            self.log(f"[WARN] Failed to save rank: {e}")

        try:
            if "points" in penner_data and penner_data["points"]:
                self._save_points(penner_data["points"])
        except Exception as e:
            self.log(f"[WARN] Failed to save points: {e}")

    def get_penner_data(self):

        from .models import Penner, Plunder

        with get_session() as s:
            penner = s.query(Penner).order_by(Penner.id.desc()).first()
            if not penner:
                return None
            plunder = s.query(Plunder).filter_by(penner_id=penner.id).all()
            penner_dict = {
                c.name: getattr(penner, c.name) for c in Penner.__table__.columns
            }
            penner_dict["plunder"] = [{"slot": p.slot, "name": p.name} for p in plunder]
            return penner_dict

    def get_activities_data(self, use_cache: bool = True):
        """
        Hole und parse die Activities-Seite (mit optionalem Caching)

        Args:
            use_cache: Wenn True, wird gecachte Daten verwendet falls verfügbar (< 30 Sekunden alt)

        Returns:
            dict: Parsed activities data (bottles, concentration, crime, overview)
        """
        from .parse import parse_activities

        if (
            use_cache
            and self._activities_cache is not None
            and self._activities_cache_time is not None
        ):
            age = datetime.now() - self._activities_cache_time
            if age.total_seconds() < self._activities_cache_ttl:
                return self._activities_cache

        try:
            response = self.api_get(self.client, "/activities/")
            activities = parse_activities(response.text)

            self._activities_cache = activities
            self._activities_cache_time = datetime.now()

            return activities
        except Exception as e:
            self.log(f"[FAIL] Failed to get activities data: {e}")
            # Return cached data on error if available
            if self._activities_cache is not None:
                return self._activities_cache
            return {}

    def get_skills_data(self):
        """
        Hole und parse die Skills-Seite für Weiterbildungen

        Returns:
            dict: Parsed skills data (running_skill, available_skills)
        """
        from .parse import parse_skills

        try:
            response = self.api_get(self.client, "/skills/")
            skills = parse_skills(response.text)
            return skills
        except Exception as e:
            self.log(f"[FAIL] Failed to get skills data: {e}")
            return {}

    def start_skill(self, skill_type: str):
        """
        Starte eine Weiterbildung (Angriff, Verteidigung oder Geschicklichkeit)

        Args:
            skill_type: "att", "def" oder "agi"

        Returns:
            dict: {"success": bool, "message": str}
        """
        if skill_type not in ["att", "def", "agi"]:
            return {
                "success": False,
                "error": "Invalid skill type. Must be att, def, or agi",
            }

        try:
            # POST zu /skill/upgrade/{skill_type}/
            response = self.api_post(
                self.client, f"/skill/upgrade/{skill_type}/", data={}
            )

            # Prüfe auf Erfolg
            if response.status_code == 200:
                # Parse die Response um zu prüfen ob es geklappt hat
                if "Es läuft bereits eine Weiterbildung" in response.text:
                    skill_names = {
                        "att": "Angriff",
                        "def": "Verteidigung",
                        "agi": "Geschicklichkeit",
                    }
                    self.log(f"[OK] Weiterbildung {skill_names[skill_type]} gestartet")

                    # OPTIMIERUNG: Parse Counter aus Response statt neuem Request
                    try:
                        counters = parse_header_counters(response.text)
                        self._update_activity_status(counters)
                        self._status_cache_time = datetime.now()
                    except Exception as e:
                        self.log(f"⚠️ Could not parse counters: {e}")

                    return {
                        "success": True,
                        "message": f"Weiterbildung {skill_names[skill_type]} gestartet",
                    }
                else:
                    return {
                        "success": False,
                        "error": "Weiterbildung konnte nicht gestartet werden",
                    }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            self.log(f"[FAIL] Failed to start skill {skill_type}: {e}")
            return {"success": False, "error": str(e)}

    def cancel_skill(self):
        """
        Beende die laufende Weiterbildung

        Returns:
            dict: {"success": bool, "message": str}
        """
        try:
            # POST zu /skill/cancel/ mit skill_num=1
            response = self.api_post(
                self.client, "/skill/cancel/", data={"skill_num": "1"}
            )

            if response.status_code == 200:
                # Prüfe auf Erfolg
                if (
                    "cancel_success" in str(response.url)
                    or "Weiterbildung" not in response.text
                    or "Es läuft bereits eine Weiterbildung" not in response.text
                ):
                    self.log("[OK] Weiterbildung abgebrochen")

                    # OPTIMIERUNG: Parse Counter aus Response statt neuem Request
                    try:
                        counters = parse_header_counters(response.text)
                        self._update_activity_status(counters)
                        self._status_cache_time = datetime.now()
                    except Exception as e:
                        self.log(f"⚠️ Could not parse counters: {e}")

                    return {
                        "success": True,
                        "message": "Weiterbildung erfolgreich abgebrochen",
                    }
                else:
                    return {
                        "success": False,
                        "error": "Weiterbildung konnte nicht abgebrochen werden",
                    }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            self.log(f"[FAIL] Failed to cancel skill: {e}")
            return {"success": False, "error": str(e)}

    def get_drinks_data(self):
        """
        Hole und parse die verfügbaren Getränke aus dem Inventar

        Returns:
            dict: {"drinks": [...], "current_promille": float}
        """
        from .parse import parse_drinks, parse_promille

        try:
            response = self.api_get(self.client, "/stock/")
            drinks_data = parse_drinks(response.text)

            # Füge aktuellen Promillewert hinzu
            current_promille = parse_promille(response.text)
            drinks_data["current_promille"] = current_promille

            return drinks_data
        except Exception as e:
            self.log(f"[FAIL] Failed to get drinks data: {e}")
            return {"drinks": [], "current_promille": 0.0}

    def drink(self, item_name: str, item_id: str, promille: str, amount: int = 1):
        """
        Trinke ein Getränk aus dem Inventar

        Args:
            item_name: Name des Getränks (z.B. "Bier", "Wodka")
            item_id: ID des Items
            promille: Promillewert als String (z.B. "35", "250")
            amount: Anzahl zu trinken (Standard: 1)

        Returns:
            dict: {"success": bool, "message": str, "new_promille": float}
        """
        from .parse import parse_promille

        try:
            self.log("[DRINK] Drinking {amount}x {item_name}...")

            response = self.api_post(
                self.client,
                "/stock/foodstuffs/use/",
                data={
                    "item": item_name,
                    "promille": promille,
                    "id": item_id,
                    "menge": str(amount),
                },
            )

            if response.status_code == 200:
                # Parse neuen Promillewert
                new_promille = parse_promille(response.text)

                # Prüfe ob Krankenhaus
                if "Krankenhaus" in response.text or new_promille >= 4.0:
                    self.log("[HOSP] Warning: Too much drunk! Hospital danger!")
                    return {
                        "success": False,
                        "error": "Zu viel getrunken! Du bist im Krankenhaus gelandet!",
                        "new_promille": new_promille,
                    }

                promille_effect = float(promille) / 100.0 * amount
                self.log(
                    f"✅ {amount}x {item_name} getrunken (+{promille_effect:.2f}‰, jetzt: {new_promille:.2f}‰)"
                )

                # OPTIMIERUNG: Parse Counter aus Response statt neuem Request
                try:
                    counters = parse_header_counters(response.text)
                    self._update_activity_status(counters)
                    self._status_cache_time = datetime.now()
                except Exception as e:
                    self.log(f"⚠️ Could not parse counters: {e}")

                return {
                    "success": True,
                    "message": f"{amount}x {item_name} getrunken",
                    "new_promille": new_promille,
                }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            self.log(f"[FAIL] Failed to drink {item_name}: {e}")
            return {"success": False, "error": str(e)}

    def pump_stomach(self):
        """
        Lasse den Magen auspumpen (setzt Promille auf 0)
        Kostet €500.00 ohne Krankenversicherung

        Returns:
            dict: {"success": bool, "message": str, "new_promille": float, "cost": str}
        """
        from .parse import parse_promille

        try:
            self.log("[HOSP] Pumping stomach...")

            response = self.api_post(
                self.client,
                "/city/medicine/help/",
                data={"id": "2", "submitForm": "Für €500.00 durchführen"},
            )

            if response.status_code == 200:
                # Parse neuen Promillewert (sollte 0 oder sehr niedrig sein)
                new_promille = parse_promille(response.text)

                # Prüfe auf Erfolgsmeldung
                if "Magen ausgepumpt" in response.text or "ausgepumpt" in response.text:
                    self.log(f"[OK] Stomach pumped! Promille: {new_promille:.2f}‰")

                    # OPTIMIERUNG: Parse Counter aus Response statt neuem Request
                    try:
                        counters = parse_header_counters(response.text)
                        self._update_activity_status(counters)
                        self._status_cache_time = datetime.now()
                    except Exception as e:
                        self.log(f"⚠️ Could not parse counters: {e}")

                    return {
                        "success": True,
                        "message": "Magen wurde ausgepumpt",
                        "new_promille": new_promille,
                        "cost": "€500.00",
                    }
                else:
                    return {
                        "success": False,
                        "error": "Konnte Magen nicht auspumpen. Vielleicht nicht genug Geld?",
                        "new_promille": new_promille,
                    }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            self.log(f"[FAIL] Failed to pump stomach: {e}")
            return {"success": False, "error": str(e)}

    def get_food_data(self):
        """
        Hole und parse die verfügbaren Essen aus dem Inventar

        Returns:
            dict: {"food": [...], "current_promille": float}
        """
        from .parse import parse_food, parse_promille

        try:
            response = self.api_get(self.client, "/stock/foodstuffs/food/")
            food_data = parse_food(response.text)

            # Füge aktuellen Promillewert hinzu
            current_promille = parse_promille(response.text)
            food_data["current_promille"] = current_promille

            return food_data
        except Exception as e:
            self.log(f"[FAIL] Failed to get food data: {e}")
            return {"food": [], "current_promille": 0.0}

    def eat_food(self, item_name: str, item_id: str, promille: str, amount: int = 1):
        """
        Esse ein Essen aus dem Inventar (senkt Promille)

        Args:
            item_name: Name des Essens (z.B. "Brot", "Currywurst", "Hamburger")
            item_id: ID des Items
            promille: Promillewert als String (z.B. "-35", "-100", "-200")
            amount: Anzahl zu essen (Standard: 1)

        Returns:
            dict: {"success": bool, "message": str, "new_promille": float}
        """
        from .parse import parse_promille

        try:
            self.log(f"[EAT] Eating {amount}x {item_name}...")

            response = self.api_post(
                self.client,
                "/stock/foodstuffs/use/",
                data={
                    "item": item_name,
                    "promille": promille,
                    "id": item_id,
                    "menge": str(amount),
                },
            )

            if response.status_code == 200:
                # Parse neuen Promillewert
                new_promille = parse_promille(response.text)

                promille_effect = float(promille) / 100.0 * amount
                self.log(
                    f"✅ {amount}x {item_name} gegessen ({promille_effect:.2f}‰, jetzt: {new_promille:.2f}‰)"
                )

                # OPTIMIERUNG: Parse Counter aus Response statt neuem Request
                try:
                    counters = parse_header_counters(response.text)
                    self._update_activity_status(counters)
                    self._status_cache_time = datetime.now()
                except Exception as e:
                    self.log(f"⚠️ Could not parse counters: {e}")

                return {
                    "success": True,
                    "message": f"{amount}x {item_name} gegessen",
                    "new_promille": new_promille,
                }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            self.log(f"[FAIL] Failed to eat {item_name}: {e}")
            return {"success": False, "error": str(e)}

    def sober_up_with_food(self, target_promille: float = 0.0):
        """
        Automatisches Ausnüchtern durch Essen
        Wählt automatisch das beste Essen basierend auf:
        - Größte Promille-Reduktion zuerst (Hamburger > Currywurst > Brot)
        - Verfügbarkeit im Inventar
        - Kosteneffizienz

        Args:
            target_promille: Ziel-Promillewert (Default: 0.0)

        Returns:
            dict: {"success": bool, "message": str, "current_promille": float, "ate": bool}
        """
        try:
            self.log("[AUTO-EAT] Target...")

            # Hole Essen aus Inventar
            food_data = self.get_food_data()
            current_promille = food_data.get("current_promille", 0.0)
            available_food = food_data.get("food", [])

            self.log(f"[STAT] Current: {current_promille:.2f}‰")

            # Prüfe ob bereits im Zielbereich oder darunter
            if current_promille <= target_promille:
                self.log(
                    f"✅ Promille bereits niedrig genug ({current_promille:.2f}‰ <= {target_promille:.2f}‰)"
                )
                return {
                    "success": True,
                    "message": f"Promille bereits bei {current_promille:.2f}‰",
                    "current_promille": current_promille,
                    "ate": False,
                }

            # Berechne benötigte Promille-Reduktion
            needed_reduction = current_promille - target_promille
            self.log(f"[STAT] Needed: -{needed_reduction:.2f}‰")

            # Keine Essen verfügbar?
            if not available_food:
                self.log("[WARN] No food in inventory!")
                return {
                    "success": False,
                    "message": "Kein Essen verfügbar",
                    "current_promille": current_promille,
                    "ate": False,
                }

            # Sortiere Essen nach Effekt (stärkste Reduktion zuerst)
            # z.B. Hamburger (-2.0‰) > Currywurst (-1.0‰) > Brot (-0.35‰)
            available_food.sort(key=lambda f: f.get("effect", 0.0))

            total_ate = False
            food_consumed = []

            # STRATEGIE: Esse vom stärksten zum schwächsten für optimale Effizienz
            for food_item in available_food:
                if current_promille <= target_promille:
                    break  # Ziel erreicht

                food_name = food_item.get("name", "")
                food_id = food_item.get("item_id", "")
                food_promille = food_item.get("promille", "0")
                food_effect = food_item.get("effect", 0.0)  # Negativ, z.B. -2.0
                food_count = food_item.get("count", 0)

                if food_count <= 0:
                    continue

                # Berechne wie viele wir brauchen
                remaining_reduction = current_promille - target_promille
                # effect ist negativ, also abs()
                amount_needed = int(abs(remaining_reduction / food_effect)) + 1
                amount_to_eat = min(amount_needed, food_count)

                # Prüfe ob es Sinn macht
                total_effect = food_effect * amount_to_eat  # Negativ
                if abs(total_effect) > 0.01:  # Mindestens 0.01‰ Wirkung
                    self.log(
                        f"🍽️ Esse {amount_to_eat}x {food_name} (je {food_effect}‰)"
                    )

                    result = self.eat_food(
                        food_name, food_id, food_promille, amount_to_eat
                    )

                    if result.get("success"):
                        current_promille = result.get("new_promille", current_promille)
                        total_ate = True
                        food_consumed.append(
                            f"{amount_to_eat}x {food_name} ({total_effect:.2f}‰)"
                        )
                        self.log(
                            f"✅ {food_name} gegessen: Jetzt bei {current_promille:.2f}‰"
                        )

            # Ergebnis
            if total_ate:
                food_str = " + ".join(food_consumed)
                self.log(
                    f"✅ Auto-Essen erfolgreich: {food_str} → {current_promille:.2f}‰"
                )
                return {
                    "success": True,
                    "message": f"Gegessen: {food_str}",
                    "current_promille": current_promille,
                    "ate": True,
                }
            else:
                self.log("[WARN] No suitable food found or already at target")
                return {
                    "success": True,
                    "message": "Bereits am Ziel oder kein passendes Essen",
                    "current_promille": current_promille,
                    "ate": False,
                }

        except Exception as e:
            self.log(f"[FAIL] Failed to sober up with food: {e}")
            return {"success": False, "error": str(e), "ate": False}

    def _save_activity_state(self, activity_type: str, is_running: bool, seconds_remaining: Optional[int] = None, activity_subtype: str = None, additional_data: Dict[str, Any] = None):
        """
        Speichere den aktuellen Zustand einer Aktivität in der Datenbank
        
        Args:
            activity_type: 'skill', 'fight', 'bottles'
            is_running: Ob die Aktivität läuft
            seconds_remaining: Verbleibende Sekunden
            activity_subtype: Untertyp (z.B. 'att', 'def', 'agi' für skills)
            additional_data: Zusätzliche Daten als JSON-String
        """
        try:
            with get_session() as s:
                # Find existing activity or create new one
                existing = s.query(BotActivity).filter_by(activity_type=activity_type).first()
                
                if is_running:
                    if existing:
                        # Update existing record
                        existing.is_running = True
                        existing.seconds_remaining = seconds_remaining
                        existing.activity_subtype = activity_subtype
                        existing.additional_data = additional_data
                        existing.updated_at = datetime.now()
                        
                        # Update expected end time if we have seconds_remaining
                        if seconds_remaining and seconds_remaining > 0:
                            existing.expected_end_time = datetime.now() + timedelta(seconds=seconds_remaining)
                        else:
                            existing.expected_end_time = None
                    else:
                        # Create new record
                        new_activity = BotActivity(
                            activity_type=activity_type,
                            activity_subtype=activity_subtype,
                            is_running=True,
                            start_time=datetime.now(),
                            seconds_remaining=seconds_remaining,
                            additional_data=additional_data
                        )
                        if seconds_remaining and seconds_remaining > 0:
                            new_activity.expected_end_time = datetime.now() + timedelta(seconds=seconds_remaining)
                        s.add(new_activity)
                else:
                    # Activity stopped - delete or update existing record
                    if existing:
                        if seconds_remaining == 0 or seconds_remaining is None:
                            # Activity completed - delete record
                            s.delete(existing)
                        else:
                            # Activity paused or interrupted - update but keep for potential resumption
                            existing.is_running = False
                            existing.seconds_remaining = seconds_remaining
                            existing.updated_at = datetime.now()
                            # Keep start_time and expected_end_time for reference
        except Exception as e:
            if "locked" not in str(e).lower():
                self.log(f"[WARN] Failed to save activity state for {activity_type}: {e}")

    def _load_activity_states(self):
        """
        Lade gespeicherte Aktivitätszustände aus der Datenbank
        Diese Methode wird beim Bot-Start aufgerufen um vorherige Zustände wiederherzustellen
        """
        try:
            with get_session() as s:
                saved_activities = s.query(BotActivity).filter_by(is_running=True).all()
                
                if not saved_activities:
                    self.log("[RESTORE] No running activities found in database")
                    return
                    
                self.log(f"[RESTORE] Found {len(saved_activities)} running activities in database")
                
                for activity in saved_activities:
                    activity_type = activity.activity_type
                    seconds_remaining = activity.seconds_remaining
                    activity_subtype = activity.activity_subtype
                    
                    # Check if the activity is still valid (not expired)
                    if activity.expected_end_time and datetime.now() > activity.expected_end_time:
                        # Activity should have finished - update database
                        activity.is_running = False
                        activity.seconds_remaining = 0
                        self.log(f"[RESTORE] Activity {activity_type} has expired")
                        continue
                    
                    # Restore the state based on activity type
                    if activity_type == "skill":
                        if seconds_remaining and seconds_remaining > 0:
                            self.skill_running = True
                            self.skill_seconds_remaining = seconds_remaining
                            # Store subtype for later use
                            self._restored_skill_subtype = activity_subtype
                            self.log(f"[RESTORE] Skill training saved: {activity_subtype}, {seconds_remaining}s remaining")
                    elif activity_type == "fight":
                        if seconds_remaining and seconds_remaining > 0:
                            self.fight_running = True
                            self.fight_seconds_remaining = seconds_remaining
                            self.log(f"[RESTORE] Fight saved: {seconds_remaining}s remaining")
                    elif activity_type == "bottles":
                        if seconds_remaining and seconds_remaining > 0:
                            self.bottles_running = True
                            self.bottles_seconds_remaining = seconds_remaining
                            self.log(f"[RESTORE] Bottle collecting saved: {seconds_remaining}s remaining")
                            
                # Clean up expired activities
                expired_activities = s.query(BotActivity).filter(
                    BotActivity.expected_end_time < datetime.now()
                ).all()
                
                for expired in expired_activities:
                    self.log(f"[CLEAN] Cleaning up expired activity: {expired.activity_type}")
                    s.delete(expired)
                    
        except Exception as e:
            if "locked" not in str(e).lower():
                self.log(f"[WARN] Failed to load activity states: {e}")

    def _restore_interrupted_workflows(self):
        """
        Versuche unterbrochene Workflows fortzusetzen
        Diese Methode wird nach dem Laden der Aktivitätszustände aufgerufen
        """
        try:
            # Markiere die ursprünglichen Zustände bevor wir sie verifizieren
            self._restored_skill_running = self.skill_running
            self._restored_skill_subtype = None  # Initialize for non-skill activities
            self._restored_fight_running = self.fight_running
            self._restored_bottles_running = self.bottles_running
            
            # Log restored state before verification
            self.log(
                f"[RESTORE] Before verification - skill={self.skill_running}, "
                f"fight={self.fight_running}, bottles={self.bottles_running}"
            )
            
            # Check if we need to refresh the game state to verify activities are still running
            if (self.skill_running or self.fight_running or self.bottles_running):
                self.log("[SYNC] Verifying restored activity states with game server...")
                
                # Refresh status to get accurate current state from the game
                if self.refresh_status(force=True):
                    # After refresh, compare with restored state
                    # Only clean up DB if game confirms activity is NOT running
                    if not self.skill_running and self._restored_skill_running:
                        self._save_activity_state("skill", False, 0, self._restored_skill_subtype)
                        self.log("[RESTORE] Skill was interrupted - will restart when training enabled")
                    if not self.fight_running and self._restored_fight_running:
                        self._save_activity_state("fight", False, 0)
                        self.log("[RESTORE] Fight was interrupted")
                    if not self.bottles_running and self._restored_bottles_running:
                        self._save_activity_state("bottles", False, 0)
                        self.log("[RESTORE] Bottle collecting was interrupted - will restart")
                    
                    # If game server says activity IS still running, use that time
                    # This handles the case where the game server continued the activity
                    if self.skill_running and self._restored_skill_running:
                        self.log(f"[RESTORE] Skill still running on game server - {self.skill_seconds_remaining}s remaining")
                    if self.fight_running and self._restored_fight_running:
                        self.log(f"[RESTORE] Fight still running on game server - {self.fight_seconds_remaining}s remaining")
                    if self.bottles_running and self._restored_bottles_running:
                        self.log(f"[RESTORE] Bottle collecting still running on game server - {self.bottles_seconds_remaining}s remaining")
                        
                    # Log current activity status after verification
                    if self.skill_running:
                        remaining = self.skill_seconds_remaining or 0
                        self.log(f"[SYNC] Skill training active - {remaining}s remaining")
                    if self.fight_running:
                        remaining = self.fight_seconds_remaining or 0
                        self.log(f"[SYNC] Fight active - {remaining}s remaining")
                    if self.bottles_running:
                        remaining = self.bottles_seconds_remaining or 0
                        self.log(f"[SYNC] Bottle collecting active - {remaining}s remaining")
                        
                    # Berechne tatsächliche verbleibende Zeit unter Berücksichtigung der vergangenen Zeit
                    # Setze Marker für Scheduler um fortzusetzen
                    self._pending_activity_resume = {
                        "bottles": {
                            "running": self.bottles_running,
                            "seconds_remaining": self.bottles_seconds_remaining or 0
                        },
                        "skill": {
                            "running": self.skill_running,
                            "seconds_remaining": self.skill_seconds_remaining or 0,
                            "subtype": self._restored_skill_subtype
                        },
                        "fight": {
                            "running": self.fight_running,
                            "seconds_remaining": self.fight_seconds_remaining or 0
                        }
                    }
                    
                    self.log(f"[RESTORE] Pending resume: bottles={self._pending_activity_resume['bottles']}, skill={self._pending_activity_resume['skill']}")
                    self.log("[SYNC] Activity states restored - scheduler will continue when activities complete")
                    
                else:
                    self.log("[WARN] Could not verify restored activities with game server")
                    
        except Exception as e:
            self.log(f"[WARN] Failed to restore interrupted workflows: {e}")
            import traceback
            traceback.print_exc()

    def get_pending_activity_resume(self) -> Optional[Dict[str, Any]]:
        """
        Gibt Informationen über fortzusetzende Aktivitäten zurück und bereinigt den Status
        
        Returns:
            dict mit info über laufende Aktivitäten oder None wenn nichts ausstehend
        """
        if not hasattr(self, '_pending_activity_resume'):
            return None
        
        pending = self._pending_activity_resume
        del self._pending_activity_resume
        
        return pending

    def get_resume_info(self) -> Dict[str, Any]:
        """
        Gibt Informationen über fortzusetzende Aktivitäten zurück
        
        Returns:
            dict mit info über laufende Aktivitäten und empfohlene Aktionen
        """
        from src.db import get_session
        from src.models import BotActivity, BotConfig
        
        result = {
            "has_running_activities": False,
            "activities": [],
            "config_check_needed": True,
        }
        
        try:
            with get_session() as s:
                # Hole Config
                config = s.query(BotConfig).first()
                if not config:
                    return result
                
                # Hole laufende Aktivitäten aus DB
                running_activities = s.query(BotActivity).filter_by(is_running=True).all()
                
                activities_info = []
                for activity in running_activities:
                    if activity.expected_end_time and datetime.now() > activity.expected_end_time:
                        # Aktivität sollte beendet sein
                        activity.is_running = False
                        continue
                    
                    activity_info = {
                        "type": activity.activity_type,
                        "subtype": activity.activity_subtype,
                        "seconds_remaining": activity.seconds_remaining or 0,
                        "expected_end": activity.expected_end_time.isoformat() if activity.expected_end_time else None,
                    }
                    activities_info.append(activity_info)
                
                result["has_running_activities"] = len(activities_info) > 0
                result["activities"] = activities_info
                result["config"] = {
                    "bottles_enabled": config.bottles_enabled,
                    "training_enabled": config.training_enabled,
                    "is_running": config.is_running,
                }
                
        except Exception as e:
            self.log(f"[WARN] Failed to get resume info: {e}")
        
        return result

    def _detect_skill_subtype(self) -> Optional[str]:
        """
        Versuche den aktuellen Skill-Subtyp zu erkennen (att, def, agi)
        
        Returns:
            Optional[str]: 'att', 'def', 'agi' oder None wenn nicht erkannt
        """
        try:
            skills_data = self.get_skills_data()
            running_skill = skills_data.get("running_skill")
            
            if running_skill and isinstance(running_skill, dict):
                skill_name = running_skill.get("name", "").lower()
                
                if "angriff" in skill_name or "att" in skill_name:
                    return "att"
                elif "verteidigung" in skill_name or "def" in skill_name:
                    return "def" 
                elif "geschicklichkeit" in skill_name or "agi" in skill_name:
                    return "agi"
                    
        except Exception as e:
            self.log(f"[WARN] Could not detect skill subtype: {e}")
            
        return None
