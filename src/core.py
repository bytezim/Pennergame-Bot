"""Core bot functionality for Pennergame automation."""

import sys
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from .constants import (
    BASE_URL,
    CACHE_TTL_ACTIVITIES,
    CACHE_TTL_LOGIN,
    CACHE_TTL_STATUS,
    DEFAULT_USER_AGENT,
)
from .db import get_session, init_db
from .logging_config import get_logger
from .models import Cookie, Log, Penner, Plunder, Settings
from .parse import parse_header_counters, parse_overview

logger = get_logger(__name__)


class PennerBot:
    """Main bot class for Pennergame automation."""

    def __init__(self) -> None:
        init_db()
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
            self.log("✅ Bot initialized successfully")
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
                    self.log("✅ Cookie successful")

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
                    self.log(f"⚠️ Failed to parse header counters: {e}")

                try:
                    self._save_bottle_price(r.text)
                except Exception as e:
                    self.log(f"⚠️ Failed to save bottle price: {e}")

                try:
                    self._save_money(r.text)
                except Exception as e:
                    self.log(f"⚠️ Failed to save money: {e}")

                return True

            self.log("❌ Cookie failed - attempting auto re-login")
            self._login_status_cache = False
            self._last_login_check = None
            return self._attempt_auto_relogin()
        except Exception as e:
            self.log(f"❌ Login check failed: {e}")
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
                self.log("🎓 Weiterbildung läuft")
                status_changed = True
                try:
                    from .events import emit_activity_started

                    emit_activity_started("skill", skill_secs)
                except Exception:
                    pass
            self.skill_running = True
            self.skill_seconds_remaining = skill_secs
        else:
            if self.skill_running:
                self.log("✅ Weiterbildung beendet")
                status_changed = True
                try:
                    from .events import emit_activity_completed

                    emit_activity_completed("skill")
                except Exception:
                    pass
            self.skill_running = False
            self.skill_seconds_remaining = None

        # Kämpfe
        fight_secs = counters.get("fight_seconds")
        if fight_secs is not None and fight_secs > 0:
            if not self.fight_running:
                self.log("⚔️ Kampf läuft")
                status_changed = True
                try:
                    from .events import emit_activity_started

                    emit_activity_started("fight", fight_secs)
                except Exception:
                    pass
            self.fight_running = True
            self.fight_seconds_remaining = fight_secs
        else:
            if self.fight_running:
                self.log("✅ Kampf beendet")
                status_changed = True
                try:
                    from .events import emit_activity_completed

                    emit_activity_completed("fight")
                except Exception:
                    pass
            self.fight_running = False
            self.fight_seconds_remaining = None

        # Pfandflaschen sammeln
        bottle_secs = counters.get("bottle_seconds")
        if bottle_secs is not None and bottle_secs > 0:
            if not self.bottles_running:
                self.log("🍾 Pfandflaschen sammeln läuft")
                status_changed = True
                try:
                    from .events import emit_activity_started

                    emit_activity_started("bottles", bottle_secs)
                except Exception:
                    pass
            self.bottles_running = True
            self.bottles_seconds_remaining = bottle_secs
        else:
            if self.bottles_running:
                self.log("✅ Pfandflaschen sammeln beendet")
                status_changed = True
                try:
                    from .events import emit_activity_completed

                    emit_activity_completed("bottles")
                except Exception:
                    pass
            self.bottles_running = False
            self.bottles_seconds_remaining = None

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
                        self.log(f"❌ Failed to decrypt credentials: {e}")
                        return False

                    self.log(f"🔄 Auto re-login for {username}...")
                    return self.login(username, password)
                else:
                    self.log("⚠️ No saved credentials for auto re-login")
                    return False
        except Exception as e:
            self.log(f"❌ Auto re-login failed: {e}")
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
                self.log(f"⚠️ Failed to parse penner data: {e}")

            # Speichere Bottle-Preis (nur bei Änderung)
            try:
                self._save_bottle_price(r.text)
            except Exception as e:
                self.log(f"⚠️ Failed to save bottle price: {e}")

            # Speichere Geldbetrag (nur bei Änderung)
            try:
                self._save_money(r.text)
            except Exception as e:
                self.log(f"⚠️ Failed to save money: {e}")

            return True
        except Exception as e:
            self.log(f"❌ Failed to refresh status: {e}")
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
                self.log("⚠️ Auto-Sell: Keine Bot-Config gefunden")
                return

            if not config.is_running:
                self.log("⚠️ Auto-Sell: Bot läuft nicht (is_running=False)")
                return

            if not config.bottles_autosell_enabled:
                self.log("⚠️ Auto-Sell: Feature ist deaktiviert")
                return

            min_price = config.bottles_min_price
            self.log(
                f"🔍 Auto-Sell Check: Aktuell {current_price_cents}¢, Schwelle {min_price}¢"
            )

        # Prüfe Preis-Bedingung
        if current_price_cents < min_price:
            self.log(
                f"⏭️ Auto-Sell: Preis zu niedrig ({current_price_cents}¢ < {min_price}¢)"
            )
            return

        # Prüfe ob Flaschen vorhanden - hole von /stock/bottle/
        try:
            from .parse import parse_bottle_count

            response = self.api_get(self.client, "/stock/bottle/")
            bottle_count = parse_bottle_count(response.text)

        except Exception as e:
            self.log(f"⚠️ Auto-Sell: Fehler beim Laden der Flaschen-Daten: {e}")
            return

        self.log(f"🔍 Auto-Sell: {bottle_count} Flaschen verfügbar")

        if bottle_count <= 0:
            self.log("⏭️ Auto-Sell: Keine Flaschen zum Verkaufen")
            return

        # Bedingungen erfüllt! Führe Auto-Sell aus
        self.log(
            f"💎 Auto-Sell Trigger: {bottle_count} Flaschen @ {current_price_cents}¢ (Schwelle: {min_price}¢)"
        )

        # Führe Verkauf direkt aus (nicht über Scheduler)
        try:
            from .tasks import sell_bottles

            result = sell_bottles(self, bottle_count)

            if result.get("success"):
                self.log(f"✅ Auto-Sell: €{result.get('earned', '0')} erwirtschaftet")
            else:
                self.log(f"❌ Auto-Sell fehlgeschlagen: {result.get('message')}")
        except Exception as e:
            self.log(f"❌ Auto-Sell Fehler: {e}")

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

            self.log(f"💰 Bottle price changed: {current_price} Cent")

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
                self.log(f"⚠️ Auto-Sell check error: {e}")
        except Exception as e:
            if "locked" not in str(e).lower():
                self.log(f"⚠️ Failed to save bottle price: {e}")

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

            self.log(f"💶 Money changed: €{current_money:,.2f}")

            # Emit Event
            try:
                from .events import emit_money_changed

                emit_money_changed(current_money)
            except Exception:
                pass
        except Exception as e:
            # Vermeide Logging wenn DB locked
            if "locked" not in str(e).lower():
                self.log(f"⚠️ Failed to save money: {e}")

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

            self.log(f"🏆 Rank changed: {rank}")
        except Exception as e:
            if "locked" not in str(e).lower():
                self.log(f"⚠️ Failed to save rank: {e}")

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

            self.log(f"⭐ Points changed: {points:,}")
        except Exception as e:
            if "locked" not in str(e).lower():
                self.log(f"⚠️ Failed to save points: {e}")

    def _save_cookies(self):
        cookies_dict = dict(self.client.cookies.items())
        with get_session() as s:
            s.query(Cookie).delete()
            for k, v in cookies_dict.items():
                s.add(Cookie(name=k, value=v))
            s.commit()

    def _load_cookies(self):
        with get_session() as s:
            cookies = s.query(Cookie).all()
            for cookie in cookies:
                self.client.cookies.set(cookie.name, cookie.value)

    def log(self, msg: str):
        # Handle Unicode for Windows console
        safe_msg = self._make_unicode_safe(msg)
        print("[PennerBot.log]", safe_msg)
        try:
            from datetime import timedelta

            with get_session() as s:
                log_entry = Log(message=msg, timestamp=datetime.now())
                s.add(log_entry)
                s.commit()

                # Lösche Logs älter als 24 Stunden (alle 50 Logs)
                # Effizienz: Nicht bei jedem Log, sondern nur gelegentlich
                log_count = s.query(Log).count()
                if log_count % 50 == 0:  # Alle 50 Logs prüfen
                    cutoff_time = datetime.now() - timedelta(hours=24)
                    old_logs = s.query(Log).filter(Log.timestamp < cutoff_time).all()
                    for old_log in old_logs:
                        s.delete(old_log)
                    if old_logs:
                        s.commit()

            # Emit Event für UI
            try:
                from .events import emit_log_added

                emit_log_added(msg)
            except Exception:
                pass  # Events sind optional
        except Exception as e:
            print("DB log failed:", e)
    
    def _make_unicode_safe(self, text: str) -> str:
        """Make text safe for Windows console output by replacing problematic Unicode characters"""
        if sys.platform == "win32":
            # Replace common emoji characters with ASCII equivalents
            emoji_replacements = {
                '✅': '[OK]',
                '❌': '[ERROR]',
                '⚠️': '[WARN]',
                '🔍': '[SEARCH]',
                '⏭️': '[SKIP]',
                '💎': '[DIAMOND]',
                '💰': '[MONEY]',
                '💶': '[MONEY]',
                '🏆': '[RANK]',
                '⭐': '[POINTS]',
                '🔐': '[LOCK]',
                '🔄': '[REFRESH]',
                '🎓': '[STUDY]',
                '⚔️': '[FIGHT]',
                '🍾': '[BOTTLES]',
                '🍺': '[DRINK]',
                '🍔': '[FOOD]',
                '🍽️': '[EAT]',
                '📊': '[STATS]',
                '📉': '[DOWN]',
                '🏥': '[HOSPITAL]',
                '🤖': '[BOT]',
                '🐍': '[PYTHON]',
                '🌐': '[WEB]',
                '👋': '[BYE]'
            }
            for emoji, replacement in emoji_replacements.items():
                text = text.replace(emoji, replacement)
        return text

    def login(self, username: str, password: str):
        print("PennerBot.login called")
        try:
            # Direkt login - kein vorheriger GET auf / notwendig
            self.log(f"🔐 Logging in as {username}")
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
                self.log("✅ Login successful")
                self._save_cookies()

                # Save credentials ENCRYPTED
                from src.security import CredentialEncryption
                
                with get_session() as s:
                    s.query(Settings).filter_by(key="username").delete()
                    s.query(Settings).filter_by(key="password_encrypted").delete()
                    s.add(Settings(key="username", value=username))
                    s.add(Settings(key="password_encrypted", value=CredentialEncryption.encrypt(password)))
                    # Context manager commits automatically

                try:
                    self.set_penner_data(self.request.text)
                except Exception as e:
                    self.log(f"⚠️ Failed to parse penner data: {e}")
                return True
            else:
                self.log("❌ Login failed")
                return False
        except Exception as e:
            self.log(f"❌ Login error: {e}")
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
            self.log(f"⚠️ Failed to save rank: {e}")

        try:
            if "points" in penner_data and penner_data["points"]:
                self._save_points(penner_data["points"])
        except Exception as e:
            self.log(f"⚠️ Failed to save points: {e}")

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
            self.log(f"❌ Failed to get activities data: {e}")
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
            self.log(f"❌ Failed to get skills data: {e}")
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
                    self.log(f"✅ Weiterbildung {skill_names[skill_type]} gestartet")

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
            self.log(f"❌ Failed to start skill {skill_type}: {e}")
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
                    self.log("✅ Weiterbildung abgebrochen")

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
            self.log(f"❌ Failed to cancel skill: {e}")
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
            self.log(f"❌ Failed to get drinks data: {e}")
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
            self.log(f"🍺 Trinke {amount}x {item_name}...")

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
                    self.log("🏥 Achtung: Zu viel getrunken! Krankenhaus-Gefahr!")
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
            self.log(f"❌ Failed to drink {item_name}: {e}")
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
            self.log("🏥 Pumpe Magen aus...")

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
                    self.log(f"✅ Magen ausgepumpt! Promille: {new_promille:.2f}‰")

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
            self.log(f"❌ Failed to pump stomach: {e}")
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
            self.log(f"❌ Failed to get food data: {e}")
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
            self.log(f"🍔 Esse {amount}x {item_name}...")

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
            self.log(f"❌ Failed to eat {item_name}: {e}")
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
            self.log(f"🍔 Auto-Essen: Ziel {target_promille:.2f}‰...")

            # Hole Essen aus Inventar
            food_data = self.get_food_data()
            current_promille = food_data.get("current_promille", 0.0)
            available_food = food_data.get("food", [])

            self.log(f"📊 Aktuell: {current_promille:.2f}‰")

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
            self.log(f"📉 Benötigt: -{needed_reduction:.2f}‰")

            # Keine Essen verfügbar?
            if not available_food:
                self.log("⚠️ Kein Essen im Inventar!")
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
                self.log("⚠️ Kein passendes Essen gefunden oder bereits am Ziel")
                return {
                    "success": True,
                    "message": "Bereits am Ziel oder kein passendes Essen",
                    "current_promille": current_promille,
                    "ate": False,
                }

        except Exception as e:
            self.log(f"❌ Failed to sober up with food: {e}")
            return {"success": False, "error": str(e), "ate": False}
