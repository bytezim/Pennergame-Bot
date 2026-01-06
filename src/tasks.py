import re
from datetime import datetime

from bs4 import BeautifulSoup

from .db import get_session
from .models import Settings


def search_bottles(bot, time_minutes: int = 10):
    from .parse import parse_activities, parse_header_counters

    try:
        bot.log(f"🍾 Starte Pfandflaschen sammeln ({time_minutes} Minuten)...")

        valid_times = [10, 30, 60, 180, 360, 540, 720]
        if time_minutes not in valid_times:
            bot.log(f"⚠️ Ungültige Zeit: {time_minutes}. Nutze 10 Minuten.")
            time_minutes = 10

        activities = bot.get_activities_data(use_cache=True)
        bottles_status = activities.get("bottles", {})

        if bottles_status.get("pending"):
            bot.log("🛒 Einkaufswagen muss erst ausgeleert werden...")

            response = bot.api_post(
                bot.client,
                "/activities/bottle/",
                data={
                    "type": "1",
                    "time": "10",
                    "bottlecollect_pending": "True",
                    "Submit2": "Einkaufswagen ausleeren",
                },
            )
            activities_after = parse_activities(response.text)
            bottles_after = activities_after.get("bottles", {})

            found_item = bottles_after.get("last_found")
            if found_item:
                bot.log(f"✨ Gefunden: {found_item}")

            bot.log("✅ Einkaufswagen ausgeleert")

            # Cache intelligent invalidieren - nur Activities
            bot._activities_cache = None
            bot._activities_cache_time = None

        response = bot.api_post(
            bot.client,
            "/activities/bottle/",
            data={"sammeln": str(time_minutes), "konzentrieren": "1"},
        )

        bot.log(f"✅ Pfandflaschen sammeln gestartet ({time_minutes} Minuten)")

        activities_new = parse_activities(response.text)
        bot._activities_cache = activities_new
        bot._activities_cache_time = datetime.now()

        try:
            counters = parse_header_counters(response.text)
            bot._update_activity_status(counters)
            bot._status_cache_time = datetime.now()
        except Exception as e:
            bot.log(f"⚠️ Could not parse counters from response: {e}")

        return {
            "success": True,
            "message": f"Pfandflaschen sammeln gestartet ({time_minutes} Minuten)",
            "time_minutes": time_minutes,
        }

    except Exception as e:
        error_msg = f"❌ Fehler beim Pfandflaschen sammeln: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def get_bottles_status(bot, force_refresh: bool = False):
    try:
        use_cache = not force_refresh
        activities = bot.get_activities_data(use_cache=use_cache)

        return {
            "success": True,
            "bottles": activities.get("bottles", {}),
            "overview": activities.get("overview", {}),
        }
    except Exception as e:
        bot.log(f"❌ Fehler beim Abrufen des Status: {e}")
        return {"success": False, "error": str(e)}


def cancel_bottle_collecting(bot):
    from .parse import parse_activities, parse_header_counters

    try:
        bot.log("🛑 Breche Pfandflaschensammeln ab...")

        response = bot.api_post(
            bot.client,
            "/activities/bottle/",
            data={"cancel": "1", "Submit2": "Abbrechen"},
        )

        # OPTIMIERUNG: Parse Response direkt statt Cache invalidieren + neuen Request
        activities = parse_activities(response.text)
        bot._activities_cache = activities
        bot._activities_cache_time = datetime.now()

        bottles_status = activities.get("bottles", {})

        # Parse Header-Counter aus Response
        try:
            counters = parse_header_counters(response.text)
            bot._update_activity_status(counters)
            bot._status_cache_time = datetime.now()
        except Exception as e:
            bot.log(f"⚠️ Could not parse counters from response: {e}")

        if not bottles_status.get("collecting"):
            bot.log("✅ Pfandflaschensammeln abgebrochen")
            return {"success": True, "message": "Pfandflaschensammeln abgebrochen"}
        else:
            bot.log("⚠️ Abbruch möglicherweise fehlgeschlagen")
            return {
                "success": False,
                "message": "Abbruch fehlgeschlagen - Status noch aktiv",
            }

    except Exception as e:
        error_msg = f"❌ Fehler beim Abbrechen: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def start_concentration(bot, mode: str = "none"):
    from .parse import parse_activities, parse_header_counters

    try:
        mode_map = {"none": "1", "fight": "2", "bottles": "3"}

        if mode not in mode_map:
            bot.log(f"⚠️ Ungültiger Modus: {mode}. Nutze 'none'.")
            mode = "none"

        konzentrieren_value = mode_map[mode]

        bot.log(f"🧠 Starte Konzentrationsmodus (Nebenbeschäftigung: {mode})...")

        response = bot.api_post(
            bot.client,
            "/activities/concentrate/",
            data={"sammeln": "10", "konzentrieren": konzentrieren_value},
        )

        if (
            "Du bist konzentriert" in response.text
            or "konzentrierst dich gerade" in response.text
        ):
            bot.log("✅ Konzentrationsmodus gestartet")

            # OPTIMIERUNG: Parse Response direkt
            activities = parse_activities(response.text)
            bot._activities_cache = activities
            bot._activities_cache_time = datetime.now()

            try:
                counters = parse_header_counters(response.text)
                bot._update_activity_status(counters)
                bot._status_cache_time = datetime.now()
            except Exception as e:
                bot.log(f"⚠️ Could not parse counters: {e}")

            mode_names = {
                "none": "Keine",
                "fight": "Kämpfen",
                "bottles": "Pfandflaschensammeln",
            }

            return {
                "success": True,
                "message": f"Konzentrationsmodus gestartet (Nebenbeschäftigung: {mode_names[mode]})",
            }
        else:
            bot.log("⚠️ Konzentrationsmodus konnte nicht gestartet werden")
            return {
                "success": False,
                "message": "Konzentrationsmodus konnte nicht gestartet werden",
            }

    except Exception as e:
        error_msg = f"❌ Fehler beim Starten des Konzentrationsmodus: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def stop_concentration(bot):
    from .parse import parse_activities, parse_header_counters

    try:
        bot.log("🛑 Beende Konzentrationsmodus...")

        with get_session() as s:
            username_setting = s.query(Settings).filter_by(key="username").first()
            if not username_setting:
                return {"success": False, "message": "Kein Username gespeichert"}
            username = username_setting.value

        response = bot.api_post(
            bot.client,
            "/activities/concentrate/",
            data={"cancel_confirmation": username},
        )

        # OPTIMIERUNG: Parse Response direkt
        activities = parse_activities(response.text)
        bot._activities_cache = activities
        bot._activities_cache_time = datetime.now()

        concentration_status = activities.get("concentration", {})

        try:
            counters = parse_header_counters(response.text)
            bot._update_activity_status(counters)
            bot._status_cache_time = datetime.now()
        except Exception as e:
            bot.log(f"⚠️ Could not parse counters: {e}")

        if not concentration_status.get("active", False):
            bot.log("✅ Konzentrationsmodus beendet")
            return {"success": True, "message": "Konzentrationsmodus beendet"}
        else:
            bot.log("⚠️ Konzentrationsmodus konnte nicht beendet werden")
            return {
                "success": False,
                "message": "Konzentrationsmodus konnte nicht beendet werden",
            }

    except Exception as e:
        error_msg = f"❌ Fehler beim Beenden des Konzentrationsmodus: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def get_concentration_status(bot, force_refresh: bool = False):
    try:
        use_cache = not force_refresh
        activities = bot.get_activities_data(use_cache=use_cache)

        return {"success": True, "concentration": activities.get("concentration", {})}
    except Exception as e:
        bot.log(f"❌ Fehler beim Abrufen des Konzentrationsstatus: {e}")
        return {"success": False, "error": str(e)}


def sell_bottles(bot, amount: int):
    """Pfandflaschen verkaufen"""
    from .parse import parse_header_counters

    try:
        bot.log(f"💰 Verkaufe {amount} Pfandflaschen...")

        # OPTIMIERUNG: Nutze gecachte Activities statt neuem Request!
        # /stock/bottle/ ist teuer, nutze Cache wenn vorhanden
        activities = bot.get_activities_data(use_cache=True)
        activities.get("bottles", {})

        # Hole aktuelle Seite NUR wenn Cache zu alt oder leer
        # Dies vermeidet unnötigen Request wenn wir gerade erst Status geholt haben
        response = bot.api_get(bot.client, "/stock/bottle/")
        html = response.text

        # Parse aktuellen Preis und verfügbare Flaschen
        soup = BeautifulSoup(html, "html.parser")

        chkval_input = soup.find("input", {"name": "chkval"})
        max_input = soup.find("input", {"name": "max"})

        if not chkval_input or not max_input:
            bot.log("❌ Konnte Pfandflaschen-Daten nicht finden")
            return {"success": False, "message": "Pfandflaschen-Daten nicht gefunden"}

        current_price = int(chkval_input.get("value", 0))
        max_bottles = int(max_input.get("value", 0))

        # OPTIMIERUNG: Parse Header Counter aus GET Response
        try:
            counters = parse_header_counters(response.text)
            bot._update_activity_status(counters)
            bot._status_cache_time = datetime.now()
        except Exception as e:
            bot.log(f"⚠️ Could not parse counters from GET: {e}")

        if amount > max_bottles:
            bot.log(f"⚠️ Nur {max_bottles} Flaschen verfügbar, verkaufe alle")
            amount = max_bottles

        if amount <= 0:
            bot.log("❌ Keine Flaschen zum Verkaufen")
            return {"success": False, "message": "Keine Flaschen verfügbar"}

        # Verkaufe Flaschen
        sell_response = bot.api_post(
            bot.client,
            "/stock/bottle/sell/",
            data={
                "chkval": str(current_price),
                "max": str(max_bottles),
                "sum": str(amount),
            },
        )

        # Parse Erfolgsmeldung
        soup_result = BeautifulSoup(sell_response.text, "html.parser")
        notifyme = soup_result.find("div", {"id": "notifyme"})

        if notifyme:
            message_text = notifyme.get_text(strip=True)

            # Extrahiere Erlös aus Meldung
            earned_match = re.search(r"für €([\d,\.]+)", message_text)
            earned = earned_match.group(1) if earned_match else "0"

            bot.log(f"✅ {amount} Flaschen für €{earned} verkauft")

            # OPTIMIERUNG: Parse Header Counter aus POST Response
            try:
                counters = parse_header_counters(sell_response.text)
                bot._update_activity_status(counters)
                bot._status_cache_time = datetime.now()

                # Speichere Money + Bottle Price aus Response
                bot._save_money(sell_response.text)
                bot._save_bottle_price(sell_response.text)
            except Exception as e:
                bot.log(f"⚠️ Could not parse counters from POST: {e}")

            # Cache intelligent invalidieren
            bot._activities_cache = None
            bot._activities_cache_time = None

            return {
                "success": True,
                "message": f"{amount} Flaschen für €{earned} verkauft",
                "amount_sold": amount,
                "earned": earned,
                "bottles_remaining": max_bottles - amount,
                "current_price": current_price,
            }
        else:
            bot.log("⚠️ Verkauf möglicherweise fehlgeschlagen")
            return {"success": False, "message": "Keine Bestätigung erhalten"}

    except Exception as e:
        error_msg = f"❌ Fehler beim Verkaufen der Flaschen: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def empty_bottle_cart(bot):
    """Einkaufswagen leeren nach Pfandflaschensuche"""
    from .parse import parse_activities, parse_header_counters

    try:
        bot.log("🛒 Leere Einkaufswagen...")

        response = bot.api_post(
            bot.client,
            "/activities/bottle/",
            data={
                "type": "1",
                "time": "10",
                "bottlecollect_pending": "True",
                "Submit2": "Einkaufswagen ausleeren",
            },
        )

        # Parse Response
        activities = parse_activities(response.text)
        bot._activities_cache = activities
        bot._activities_cache_time = datetime.now()

        # OPTIMIERUNG: Parse Header Counter aus Response
        try:
            counters = parse_header_counters(response.text)
            bot._update_activity_status(counters)
            bot._status_cache_time = datetime.now()
        except Exception as e:
            bot.log(f"⚠️ Could not parse counters: {e}")

        bottles_status = activities.get("bottles", {})
        found_item = bottles_status.get("last_found")

        message = "Einkaufswagen ausgeleert"
        if found_item:
            message += f" - Gefunden: {found_item}"
            bot.log(f"✨ Gefunden: {found_item}")

        bot.log("✅ " + message)

        # Trigger Auto-Sell Check da neue Flaschen hinzugekommen sind
        try:
            from .db import get_session
            from .models import BottlePrice

            with get_session() as s:
                last_price = (
                    s.query(BottlePrice).order_by(BottlePrice.id.desc()).first()
                )
                if last_price:
                    bot._trigger_auto_sell_check(last_price.price_cents)
        except Exception as e:
            bot.log(f"⚠️ Auto-sell check after cart empty failed: {e}")

        return {
            "success": True,
            "message": message,
            "found_item": found_item,
            "pending": bottles_status.get("pending", False),
        }

    except Exception as e:
        error_msg = f"❌ Fehler beim Ausleeren des Einkaufswagens: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def get_bottles_inventory(bot):
    """
    Hole Pfandflaschen-Inventar (Anzahl und Preis)
    OPTIMIERUNG: Diese Funktion sollte vermieden werden - nutze stattdessen sell_bottles() Response
    """
    from .parse import parse_header_counters

    try:
        # Prüfe ob wir erst kürzlich /stock/bottle/ geholt haben
        # Dies vermeidet redundante Requests
        response = bot.api_get(bot.client, "/stock/bottle/")
        html = response.text

        soup = BeautifulSoup(html, "html.parser")

        # Parse verfügbare Flaschen
        chkval_input = soup.find("input", {"name": "chkval"})
        max_input = soup.find("input", {"name": "max"})

        if not chkval_input or not max_input:
            return {"success": False, "error": "Konnte Inventar-Daten nicht finden"}

        current_price = int(chkval_input.get("value", 0))
        bottle_count = int(max_input.get("value", 0))

        # OPTIMIERUNG: Parse Header Counter aus Response
        try:
            counters = parse_header_counters(response.text)
            bot._update_activity_status(counters)
            bot._status_cache_time = datetime.now()

            # Speichere Money + Bottle Price aus Response
            bot._save_money(response.text)
            bot._save_bottle_price(response.text)
        except Exception as e:
            bot.log(f"⚠️ Could not parse counters: {e}")

        # Parse Display-Text für Anzahl
        bottle_text = None
        for td in soup.find_all("td"):
            text = td.get_text(strip=True)
            if "Pfandflaschen" in text and "Preis" in text:
                bottle_text = text
                break

        return {
            "success": True,
            "bottle_count": bottle_count,
            "price_cents": current_price,
            "price_euro": current_price / 100,
            "display_text": bottle_text,
        }

    except Exception as e:
        bot.log(f"❌ Fehler beim Abrufen des Inventars: {e}")
        return {"success": False, "error": str(e)}


def start_training(bot, skill_type: str):
    """
    Starte eine Weiterbildung für den angegebenen Skill-Typ

    Args:
        bot: PennerBot instance
        skill_type: "att", "def" oder "agi"

    Returns:
        dict: {"success": bool, "message": str, "skill_type": str}
    """
    from .parse import parse_header_counters

    try:
        # Validierung
        if skill_type not in ["att", "def", "agi"]:
            error_msg = f"⚠️ Ungültiger Skill-Typ: {skill_type}"
            bot.log(error_msg)
            return {"success": False, "message": error_msg}

        skill_names = {
            "att": "Angriff",
            "def": "Verteidigung",
            "agi": "Geschicklichkeit",
        }

        bot.log(f"🎓 Starte Weiterbildung: {skill_names[skill_type]}...")

        # Prüfe ob bereits eine Weiterbildung läuft
        skills_data = bot.get_skills_data()
        if skills_data.get("running_skill"):
            running = skills_data["running_skill"]
            bot.log(
                f"⚠️ Weiterbildung läuft bereits: {running.get('name', 'Unbekannt')}"
            )
            return {
                "success": False,
                "message": f"Weiterbildung läuft bereits: {running.get('name', 'Unbekannt')}",
            }

        # Starte Weiterbildung
        response = bot.api_post(bot.client, f"/skill/upgrade/{skill_type}/", data={})

        if response.status_code == 200:
            # Parse Response um zu prüfen ob erfolgreich
            if "Es läuft bereits eine Weiterbildung" in response.text:
                bot.log(f"✅ Weiterbildung {skill_names[skill_type]} gestartet")

                # OPTIMIERUNG: Parse Counter aus Response
                try:
                    counters = parse_header_counters(response.text)
                    bot._update_activity_status(counters)
                    bot._status_cache_time = datetime.now()
                except Exception as e:
                    bot.log(f"⚠️ Could not parse counters: {e}")

                return {
                    "success": True,
                    "message": f"Weiterbildung {skill_names[skill_type]} gestartet",
                    "skill_type": skill_type,
                }
            else:
                bot.log("⚠️ Weiterbildung konnte nicht gestartet werden")
                return {
                    "success": False,
                    "message": "Weiterbildung konnte nicht gestartet werden",
                }
        else:
            return {"success": False, "message": f"HTTP {response.status_code}"}

    except Exception as e:
        error_msg = f"❌ Fehler beim Starten der Weiterbildung: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def get_training_status(bot, force_refresh: bool = False):
    """
    Hole Status der aktuellen Weiterbildung

    Args:
        bot: PennerBot instance
        force_refresh: Cache ignorieren

    Returns:
        dict: {"success": bool, "training": dict, "available_skills": dict}
    """
    try:
        skills_data = bot.get_skills_data()

        return {
            "success": True,
            "training": skills_data.get("running_skill"),
            "available_skills": skills_data.get("available_skills", {}),
        }
    except Exception as e:
        bot.log(f"❌ Fehler beim Abrufen des Weiterbildungs-Status: {e}")
        return {"success": False, "error": str(e)}


def cancel_training(bot):
    """
    Breche die laufende Weiterbildung ab

    Args:
        bot: PennerBot instance

    Returns:
        dict: {"success": bool, "message": str}
    """
    from .parse import parse_header_counters

    try:
        bot.log("🛑 Breche Weiterbildung ab...")

        # Prüfe ob überhaupt eine Weiterbildung läuft
        skills_data = bot.get_skills_data()
        if not skills_data.get("running_skill"):
            bot.log("⚠️ Keine Weiterbildung läuft")
            return {"success": False, "message": "Keine Weiterbildung läuft"}

        # Breche ab
        response = bot.api_post(bot.client, "/skill/cancel/", data={"skill_num": "1"})

        if response.status_code == 200:
            # OPTIMIERUNG: Parse Counter aus Response
            try:
                counters = parse_header_counters(response.text)
                bot._update_activity_status(counters)
                bot._status_cache_time = datetime.now()
            except Exception as e:
                bot.log(f"⚠️ Could not parse counters: {e}")

            # Prüfe ob erfolgreich
            if (
                "cancel_success" in str(response.url)
                or "Weiterbildung" not in response.text
                or "Es läuft bereits eine Weiterbildung" not in response.text
            ):
                bot.log("✅ Weiterbildung abgebrochen")
                return {"success": True, "message": "Weiterbildung abgebrochen"}
            else:
                bot.log("⚠️ Abbruch möglicherweise fehlgeschlagen")
                return {
                    "success": False,
                    "message": "Abbruch fehlgeschlagen - Status noch aktiv",
                }
        else:
            return {"success": False, "message": f"HTTP {response.status_code}"}

    except Exception as e:
        error_msg = f"❌ Fehler beim Abbrechen der Weiterbildung: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def auto_drink_before_training(bot, target_promille: float = 2.5):
    """
    Trinke automatisch Getränke um Ziel-Promille zu erreichen (für Weiterbildungen)
    Sicherheitslogik:
    - Prüft aktuellen Promillewert
    - Wählt passendes Getränk basierend auf benötigter Menge
    - Berechnet sichere Anzahl um Krankenhaus zu vermeiden
    - Stoppt bei Gefahr (>3.5‰)

    Args:
        bot: PennerBot instance
        target_promille: Ziel-Promillewert (Default: 2.5, Range: 2.0-3.0)

    Returns:
        dict: {"success": bool, "message": str, "current_promille": float, "drank": bool}
    """
    from src.constants import (
        PROMILLE_SAFE_TRAINING_MAX,
        PROMILLE_SAFE_TRAINING_MIN,
        PROMILLE_WARNING_THRESHOLD,
    )

    try:
        # Validiere target_promille
        if target_promille < PROMILLE_SAFE_TRAINING_MIN:
            target_promille = PROMILLE_SAFE_TRAINING_MIN
        elif target_promille > PROMILLE_SAFE_TRAINING_MAX:
            target_promille = PROMILLE_SAFE_TRAINING_MAX

        bot.log(f"🍺 Auto-Trinken: Ziel {target_promille:.2f}‰...")

        # Hole Getränke aus Inventar
        drinks_data = bot.get_drinks_data()
        current_promille = drinks_data.get("current_promille", 0.0)
        available_drinks = drinks_data.get("drinks", [])

        bot.log(f"📊 Aktuell: {current_promille:.2f}‰")

        # Prüfe ob bereits im Zielbereich oder zu hoch
        if current_promille >= target_promille:
            bot.log(
                f"✅ Promille bereits ausreichend ({current_promille:.2f}‰ >= {target_promille:.2f}‰)"
            )
            return {
                "success": True,
                "message": f"Promille bereits bei {current_promille:.2f}‰",
                "current_promille": current_promille,
                "drank": False,
            }

        if current_promille >= PROMILLE_WARNING_THRESHOLD:
            bot.log(f"⚠️ Promille zu hoch ({current_promille:.2f}‰), kein Trinken!")
            return {
                "success": False,
                "message": f"Promille zu hoch: {current_promille:.2f}‰",
                "current_promille": current_promille,
                "drank": False,
            }

        # Berechne benötigten Promille-Anstieg
        needed_promille = target_promille - current_promille

        # Sichere Reserve: Maximal bis 3.0‰ trinken
        safe_max_increase = PROMILLE_SAFE_TRAINING_MAX - current_promille

        if safe_max_increase <= 0:
            bot.log("⚠️ Bereits am sicheren Maximum")
            return {
                "success": True,
                "message": "Bereits am sicheren Maximum",
                "current_promille": current_promille,
                "drank": False,
            }

        # Begrenze auf sicheren Wert
        needed_promille = min(needed_promille, safe_max_increase)

        bot.log(f"📈 Benötigt: +{needed_promille:.2f}‰")

        # Keine Getränke verfügbar?
        if not available_drinks:
            bot.log("⚠️ Keine Getränke im Inventar!")
            return {
                "success": False,
                "message": "Keine Getränke verfügbar",
                "current_promille": current_promille,
                "drank": False,
            }

        # STRATEGIE: Erst Vodka (stark), dann Bier/Cola/Limo (schwach) zum Feinadjust
        # Kategorisiere Getränke
        strong_drinks = []  # Vodka, Whiskey, etc. (>= 2.0‰)
        weak_drinks = []  # Bier, Cola, Limo (<= 0.5‰)

        for drink in available_drinks:
            effect = drink.get("effect", 0.0)
            drink.get("name", "").lower()
            count = drink.get("count", 0)

            if effect <= 0 or count <= 0:
                continue

            # Stark: Vodka und ähnliche (>= 2.0‰)
            if effect >= 2.0:
                strong_drinks.append(drink)
            # Schwach: Bier, Cola, Limo (<= 0.5‰)
            elif effect <= 0.5:
                weak_drinks.append(drink)

        # Sortiere: Starke absteigend (stärkste zuerst), Schwache aufsteigend (schwächste zuerst)
        strong_drinks.sort(key=lambda d: d.get("effect", 0.0), reverse=True)
        weak_drinks.sort(key=lambda d: d.get("effect", 0.0))

        total_drank = False
        drinks_consumed = []

        # SCHRITT 1: Trinke VODKA wenn verfügbar und benötigt >= 2.0‰
        if strong_drinks and needed_promille >= 2.0:
            vodka = strong_drinks[0]  # Stärkstes Getränk (z.B. Vodka 2.5‰)
            vodka_effect = vodka.get("effect", 0.0)
            vodka_name = vodka.get("name", "Vodka")
            vodka_id = vodka.get("item_id", "")
            vodka_promille = vodka.get("promille", "0")
            vodka_count = vodka.get("count", 0)

            # Berechne wie viele Vodka wir brauchen (maximal sicher)
            # Lasse 0.5‰ Reserve für Feinadjust mit Bier
            target_with_vodka = min(needed_promille - 0.3, safe_max_increase - 0.3)
            vodka_amount = max(1, int(target_with_vodka / vodka_effect))
            vodka_amount = min(vodka_amount, vodka_count)

            # Prüfe Sicherheit
            total_vodka_effect = vodka_effect * vodka_amount
            if total_vodka_effect <= safe_max_increase:
                bot.log(
                    f"🥃 Trinke {vodka_amount}x {vodka_name} (je {vodka_effect}‰) - Hauptgetränk"
                )

                result = bot.drink(vodka_name, vodka_id, vodka_promille, vodka_amount)

                if result.get("success"):
                    current_promille = result.get("new_promille", current_promille)
                    total_drank = True
                    drinks_consumed.append(
                        f"{vodka_amount}x {vodka_name} (+{total_vodka_effect:.2f}‰)"
                    )
                    bot.log(
                        f"✅ {vodka_name} getrunken: Jetzt bei {current_promille:.2f}‰"
                    )

                    # Aktualisiere benötigten Rest
                    needed_promille = target_promille - current_promille
                    safe_max_increase = PROMILLE_SAFE_TRAINING_MAX - current_promille

        # SCHRITT 2: Feinadjust mit BIER/ wenn noch benötigt
        if needed_promille > 0.1 and safe_max_increase > 0.1 and weak_drinks:
            # Wähle schwächstes Getränk für Präzision
            weak_drink = weak_drinks[0]
            weak_effect = weak_drink.get("effect", 0.0)
            weak_name = weak_drink.get("name", "Bier")
            weak_id = weak_drink.get("item_id", "")
            weak_promille = weak_drink.get("promille", "0")
            weak_count = weak_drink.get("count", 0)

            # Berechne benötigte Menge
            weak_amount = int(needed_promille / weak_effect) + 1
            weak_amount = min(weak_amount, weak_count)

            # Prüfe Sicherheit
            total_weak_effect = weak_effect * weak_amount
            if total_weak_effect <= safe_max_increase:
                bot.log(
                    f"� Trinke {weak_amount}x {weak_name} (je {weak_effect}‰) - Feinadjust"
                )

                result = bot.drink(weak_name, weak_id, weak_promille, weak_amount)

                if result.get("success"):
                    current_promille = result.get("new_promille", current_promille)
                    total_drank = True
                    drinks_consumed.append(
                        f"{weak_amount}x {weak_name} (+{total_weak_effect:.2f}‰)"
                    )
                    bot.log(
                        f"✅ {weak_name} getrunken: Jetzt bei {current_promille:.2f}‰"
                    )

        # Ergebnis
        if total_drank:
            drinks_str = " + ".join(drinks_consumed)
            bot.log(
                f"✅ Auto-Trinken erfolgreich: {drinks_str} → {current_promille:.2f}‰"
            )
            return {
                "success": True,
                "message": f"Getrunken: {drinks_str}",
                "current_promille": current_promille,
                "drank": True,
            }
        else:
            bot.log("⚠️ Kein passendes Getränk gefunden oder bereits am Ziel")
            return {
                "success": True,
                "message": "Bereits am Ziel oder kein passendes Getränk",
                "current_promille": current_promille,
                "drank": False,
            }

    except Exception as e:
        error_msg = f"❌ Fehler beim Auto-Trinken: {e}"
        bot.log(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "current_promille": 0.0,
            "drank": False,
        }
