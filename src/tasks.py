import re
from datetime import datetime
from bs4 import BeautifulSoup
from .db import get_session
from .models import Settings


def search_bottles(bot, time_minutes: int = 10):
    from .parse import parse_activities, parse_header_counters
    from .constants import VALID_BOTTLE_DURATIONS, DEFAULT_BOTTLE_DURATION

    try:
        if bot.fight_running:
            bot.log("[INFO] Kampf laeuft - Pfandflaschen sammeln uebersprungen")
            return {
                "success": False,
                "message": "Kampf läuft - Pfandflaschen sammeln nicht möglich",
            }
        bot.log(f"[INFO] Starte Pfandflaschen sammeln ({time_minutes} Minuten)...")
        if time_minutes not in VALID_BOTTLE_DURATIONS:
            bot.log(
                f"Ungültige Zeit: {time_minutes}. Nutze {DEFAULT_BOTTLE_DURATION} Minuten."
            )
            time_minutes = DEFAULT_BOTTLE_DURATION
        activities = bot.get_activities_data(use_cache=True)
        bottles_status = activities.get("bottles", {})
        if bottles_status.get("pending"):
            bot.log("[WARN] Einkaufswagen muss erst ausgeleert werden...")
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
                bot.log(f"Gefunden: {found_item}")
            bot.log("Einkaufswagen ausgeleert")
            bot._activities_cache = None
            bot._activities_cache_time = None
        response = bot.api_post(
            bot.client,
            "/activities/bottle/",
            data={"sammeln": str(time_minutes), "konzentrieren": "1"},
        )
        bot.log(f"Pfandflaschen sammeln gestartet ({time_minutes} Minuten)")
        activities_new = parse_activities(response.text)
        bot._activities_cache = activities_new
        bot._activities_cache_time = datetime.now()
        try:
            counters = parse_header_counters(response.text)
            bot._update_activity_status(counters)
            bot._status_cache_time = datetime.now()
        except Exception as e:
            bot.log(f"Could not parse counters from response: {e}")
        return {
            "success": True,
            "message": f"Pfandflaschen sammeln gestartet ({time_minutes} Minuten)",
            "time_minutes": time_minutes,
        }
    except Exception as e:
        error_msg = f"Fehler beim Pfandflaschen sammeln: {e}"
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
        bot.log(f"Fehler beim Abrufen des Status: {e}")
        return {"success": False, "error": str(e)}


def cancel_bottle_collecting(bot):
    from .parse import parse_activities, parse_header_counters

    try:
        bot.log("Breche Pfandflaschensammeln ab...")
        response = bot.api_post(
            bot.client,
            "/activities/bottle/",
            data={"cancel": "1", "Submit2": "Abbrechen"},
        )
        activities = parse_activities(response.text)
        bot._activities_cache = activities
        bot._activities_cache_time = datetime.now()
        bottles_status = activities.get("bottles", {})
        try:
            counters = parse_header_counters(response.text)
            bot._update_activity_status(counters)
            bot._status_cache_time = datetime.now()
        except Exception as e:
            bot.log(f"Could not parse counters from response: {e}")
        if not bottles_status.get("collecting"):
            bot.log("Pfandflaschensammeln abgebrochen")
            return {"success": True, "message": "Pfandflaschensammeln abgebrochen"}
        else:
            bot.log("Abbruch möglicherweise fehlgeschlagen")
            return {
                "success": False,
                "message": "Abbruch fehlgeschlagen - Status noch aktiv",
            }
    except Exception as e:
        error_msg = f"Fehler beim Abbrechen: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def start_concentration(bot, mode: str = "none"):
    from .parse import parse_activities, parse_header_counters

    try:
        mode_map = {"none": "1", "fight": "2", "bottles": "3"}
        if mode not in mode_map:
            bot.log(f"Ungültiger Modus: {mode}. Nutze 'none'.")
            mode = "none"
        konzentrieren_value = mode_map[mode]
        bot.log(f"Starte Konzentrationsmodus (Nebenbeschäftigung: {mode})...")
        response = bot.api_post(
            bot.client,
            "/activities/concentrate/",
            data={"sammeln": "10", "konzentrieren": konzentrieren_value},
        )
        if (
            "Du bist konzentriert" in response.text
            or "konzentrierst dich gerade" in response.text
        ):
            bot.log("Konzentrationsmodus gestartet")
            activities = parse_activities(response.text)
            bot._activities_cache = activities
            bot._activities_cache_time = datetime.now()
            try:
                counters = parse_header_counters(response.text)
                bot._update_activity_status(counters)
                bot._status_cache_time = datetime.now()
            except Exception as e:
                bot.log(f"Could not parse counters: {e}")
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
            bot.log("Konzentrationsmodus konnte nicht gestartet werden")
            return {
                "success": False,
                "message": "Konzentrationsmodus konnte nicht gestartet werden",
            }
    except Exception as e:
        error_msg = f"Fehler beim Starten des Konzentrationsmodus: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def stop_concentration(bot):
    from .parse import parse_activities, parse_header_counters

    try:
        bot.log("Beende Konzentrationsmodus...")
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
        activities = parse_activities(response.text)
        bot._activities_cache = activities
        bot._activities_cache_time = datetime.now()
        concentration_status = activities.get("concentration", {})
        try:
            counters = parse_header_counters(response.text)
            bot._update_activity_status(counters)
            bot._status_cache_time = datetime.now()
        except Exception as e:
            bot.log(f"Could not parse counters: {e}")
        if not concentration_status.get("active", False):
            bot.log("Konzentrationsmodus beendet")
            return {"success": True, "message": "Konzentrationsmodus beendet"}
        else:
            bot.log("Konzentrationsmodus konnte nicht beendet werden")
            return {
                "success": False,
                "message": "Konzentrationsmodus konnte nicht beendet werden",
            }
    except Exception as e:
        error_msg = f"Fehler beim Beenden des Konzentrationsmodus: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def get_concentration_status(bot, force_refresh: bool = False):
    try:
        use_cache = not force_refresh
        activities = bot.get_activities_data(use_cache=use_cache)
        return {"success": True, "concentration": activities.get("concentration", {})}
    except Exception as e:
        bot.log(f"Fehler beim Abrufen des Konzentrationsstatus: {e}")
        return {"success": False, "error": str(e)}


def sell_bottles(bot, amount: int):
    from .parse import parse_header_counters
    from .constants import MIN_BOTTLE_PRICE_CENTS, MAX_BOTTLE_PRICE_CENTS

    try:
        bot.log(f"Verkaufe {amount} Pfandflaschen...")
        activities = bot.get_activities_data(use_cache=True)
        activities.get("bottles", {})
        response = bot.api_get(bot.client, "/stock/bottle/")
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        chkval_input = soup.find("input", {"name": "chkval"})
        max_input = soup.find("input", {"name": "max"})
        if not chkval_input or not max_input:
            bot.log("Konnte Pfandflaschen-Daten nicht finden")
            return {"success": False, "message": "Pfandflaschen-Daten nicht gefunden"}
        current_price = int(chkval_input.get("value", 0))
        max_bottles = int(max_input.get("value", 0))
        if (
            current_price < MIN_BOTTLE_PRICE_CENTS
            or current_price > MAX_BOTTLE_PRICE_CENTS
        ):
            bot.log(f"Ungültiger Flaschenpreis: {current_price} Cent")
            return {
                "success": False,
                "message": f"Ungültiger Preis: {current_price} Cent",
            }
        try:
            counters = parse_header_counters(response.text)
            bot._update_activity_status(counters)
            bot._status_cache_time = datetime.now()
        except Exception as e:
            bot.log(f"Could not parse counters from GET: {e}")
        if amount > max_bottles:
            bot.log(f"Nur {max_bottles} Flaschen verfügbar, verkaufe alle")
            amount = max_bottles
        if amount <= 0:
            bot.log("Keine Flaschen zum Verkaufen")
            return {"success": False, "message": "Keine Flaschen verfügbar"}
        sell_response = bot.api_post(
            bot.client,
            "/stock/bottle/sell/",
            data={
                "chkval": str(current_price),
                "max": str(max_bottles),
                "sum": str(amount),
            },
        )
        soup_result = BeautifulSoup(sell_response.text, "html.parser")
        notifyme = soup_result.find("div", {"id": "notifyme"})
        if notifyme:
            message_text = notifyme.get_text(strip=True)
            earned_match = re.search("für €([\\d,\\.]+)", message_text)
            earned = earned_match.group(1) if earned_match else "0"
            bot.log(f"{amount} Flaschen für €{earned} verkauft")
            try:
                counters = parse_header_counters(sell_response.text)
                bot._update_activity_status(counters)
                bot._status_cache_time = datetime.now()
                bot._save_money(sell_response.text)
                bot._save_bottle_price(sell_response.text)
            except Exception as e:
                bot.log(f"Could not parse counters from POST: {e}")
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
            bot.log("Verkauf möglicherweise fehlgeschlagen")
            return {"success": False, "message": "Keine Bestätigung erhalten"}
    except Exception as e:
        error_msg = f"Fehler beim Verkaufen der Flaschen: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def empty_bottle_cart(bot):
    from .parse import parse_activities, parse_header_counters

    try:
        bot.log("Leere Einkaufswagen...")
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
        activities = parse_activities(response.text)
        bot._activities_cache = activities
        bot._activities_cache_time = datetime.now()
        try:
            counters = parse_header_counters(response.text)
            bot._update_activity_status(counters)
            bot._status_cache_time = datetime.now()
        except Exception as e:
            bot.log(f"Could not parse counters: {e}")
        bottles_status = activities.get("bottles", {})
        found_item = bottles_status.get("last_found")
        message = "Einkaufswagen ausgeleert"
        if found_item:
            message += f" - Gefunden: {found_item}"
            bot.log(f"Gefunden: {found_item}")
        bot.log("" + message)
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
            bot.log(f"Auto-sell check after cart empty failed: {e}")
        return {
            "success": True,
            "message": message,
            "found_item": found_item,
            "pending": bottles_status.get("pending", False),
        }
    except Exception as e:
        error_msg = f"Fehler beim Ausleeren des Einkaufswagens: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def get_bottles_inventory(bot):
    from .parse import parse_header_counters
    from .constants import MIN_BOTTLE_PRICE_CENTS, MAX_BOTTLE_PRICE_CENTS

    try:
        response = bot.api_get(bot.client, "/stock/bottle/")
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        chkval_input = soup.find("input", {"name": "chkval"})
        max_input = soup.find("input", {"name": "max"})
        if not chkval_input or not max_input:
            return {"success": False, "error": "Konnte Inventar-Daten nicht finden"}
        current_price = int(chkval_input.get("value", 0))
        bottle_count = int(max_input.get("value", 0))
        if (
            current_price < MIN_BOTTLE_PRICE_CENTS
            or current_price > MAX_BOTTLE_PRICE_CENTS
        ):
            bot.log(f"Ungültiger Flaschenpreis: {current_price} Cent")
            return {
                "success": False,
                "message": f"Ungültiger Preis: {current_price} Cent",
            }
        try:
            counters = parse_header_counters(response.text)
            bot._update_activity_status(counters)
            bot._status_cache_time = datetime.now()
            bot._save_money(response.text)
            bot._save_bottle_price(response.text)
        except Exception as e:
            bot.log(f"Could not parse counters: {e}")
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
        bot.log(f"Fehler beim Abrufen des Inventars: {e}")
        return {"success": False, "error": str(e)}


def start_training(bot, skill_type: str):
    from .parse import parse_header_counters
    from .constants import VALID_TRAINING_SKILLS

    try:
        if skill_type not in VALID_TRAINING_SKILLS:
            error_msg = f"Ungültiger Skill-Typ: {skill_type}"
            bot.log(error_msg)
            return {"success": False, "message": error_msg}
        skill_names = {
            "att": "Angriff",
            "def": "Verteidigung",
            "agi": "Geschicklichkeit",
        }
        bot.log(f"Starte Weiterbildung: {skill_names[skill_type]}...")
        skills_data = bot.get_skills_data()
        if skills_data.get("running_skill"):
            running = skills_data["running_skill"]
            bot.log(f"Weiterbildung läuft bereits: {running.get('name', 'Unbekannt')}")
            return {
                "success": False,
                "message": f"Weiterbildung läuft bereits: {running.get('name', 'Unbekannt')}",
            }
        response = bot.api_post(bot.client, f"/skill/upgrade/{skill_type}/", data={})
        if response.status_code == 200:
            if "Es läuft bereits eine Weiterbildung" in response.text:
                bot.log(f"Weiterbildung {skill_names[skill_type]} gestartet")
                try:
                    counters = parse_header_counters(response.text)
                    bot._update_activity_status(counters)
                    bot._status_cache_time = datetime.now()
                except Exception as e:
                    bot.log(f"Could not parse counters: {e}")
                return {
                    "success": True,
                    "message": f"Weiterbildung {skill_names[skill_type]} gestartet",
                    "skill_type": skill_type,
                }
            else:
                bot.log("Weiterbildung konnte nicht gestartet werden")
                return {
                    "success": False,
                    "message": "Weiterbildung konnte nicht gestartet werden",
                }
        else:
            return {"success": False, "message": f"HTTP {response.status_code}"}
    except Exception as e:
        error_msg = f"Fehler beim Starten der Weiterbildung: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def get_training_status(bot, force_refresh: bool = False):
    try:
        skills_data = bot.get_skills_data()
        return {
            "success": True,
            "training": skills_data.get("running_skill"),
            "available_skills": skills_data.get("available_skills", {}),
        }
    except Exception as e:
        bot.log(f"Fehler beim Abrufen des Weiterbildungs-Status: {e}")
        return {"success": False, "error": str(e)}


def cancel_training(bot):
    from .parse import parse_header_counters

    try:
        bot.log("Breche Weiterbildung ab...")
        skills_data = bot.get_skills_data()
        if not skills_data.get("running_skill"):
            bot.log("Keine Weiterbildung läuft")
            return {"success": False, "message": "Keine Weiterbildung läuft"}
        response = bot.api_post(bot.client, "/skill/cancel/", data={"skill_num": "1"})
        if response.status_code == 200:
            try:
                counters = parse_header_counters(response.text)
                bot._update_activity_status(counters)
                bot._status_cache_time = datetime.now()
            except Exception as e:
                bot.log(f"Could not parse counters: {e}")
            if (
                "cancel_success" in str(response.url)
                or "Weiterbildung" not in response.text
                or "Es läuft bereits eine Weiterbildung" not in response.text
            ):
                bot.log("Weiterbildung abgebrochen")
                return {"success": True, "message": "Weiterbildung abgebrochen"}
            else:
                bot.log("Abbruch möglicherweise fehlgeschlagen")
                return {
                    "success": False,
                    "message": "Abbruch fehlgeschlagen - Status noch aktiv",
                }
        else:
            return {"success": False, "message": f"HTTP {response.status_code}"}
    except Exception as e:
        error_msg = f"Fehler beim Abbrechen der Weiterbildung: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def _get_last_page_link_from_pagination(bot, soup):
    pagination = soup.find("div", {"id": "pagination"})

    last_page_link = "/highscore/attackable/"  # Default to first page

    if pagination:
        page_numbers = []
        for a in pagination.find_all("a"):
            href = a.get("href", "")
            if "/highscore/attackable/" in href:
                # Extract page number from URL like "/highscore/attackable/397/"
                parts = href.strip("/").split("/")
                if len(parts) >= 3 and parts[-2] == "attackable":
                    try:
                        page_num = int(parts[-1])
                        page_numbers.append(page_num)
                    except ValueError:
                        continue

        if page_numbers:
            max_page = max(page_numbers)
            # Add trailing slash to match exact URL from HTML
            last_page_link = f"/highscore/attackable/{max_page}/"
            bot.log(
                f"Paginierung gefunden: {len(page_numbers)} Seiten, letzte Seite: {max_page}"
            )
        else:
            bot.log("Paginierung gefunden, aber keine gültigen Seitenzahlen extrahiert")
    else:
        bot.log("Keine Paginierung gefunden - verwende erste Seite")

    return last_page_link


def get_last_attackable_player(bot):
    try:
        # First, get the first page to find the last page number
        response = bot.api_get(bot.client, "/highscore/attackable/")
        soup = BeautifulSoup(response.text, "html.parser")
        last_page_link = _get_last_page_link_from_pagination(bot, soup)

        bot.log(f"Lade Seite: {last_page_link}")

        # Use the bot's api_get method
        response = bot.api_get(bot.client, last_page_link)
        bot.log(f"Response status: {response.status_code}, URL: {response.url}")

        if response.status_code != 200:
            bot.log(f"Seite konnte nicht geladen werden: HTTP {response.status_code}")
            return {
                "success": False,
                "error": f"Seite konnte nicht geladen werden: HTTP {response.status_code}",
            }

        # Debug: log response info
        bot.log(f"Content-Length: {len(response.text)}")

        # Check if response contains any HTML
        if not response.text or "<table" not in response.text.lower():
            bot.log("Response enthält keine Tabellen")
            bot.log(f"Response-Vorschau: {response.text[:500]}")
            return {"success": False, "error": "Seite enthält keine gültigen Daten"}

        soup = BeautifulSoup(response.text, "html.parser")
        bot.log(f"Response status: {response.status_code}, URL: {response.url}")

        if response.status_code != 200:
            bot.log(f"Seite konnte nicht geladen werden: HTTP {response.status_code}")
            return {
                "success": False,
                "error": f"Seite konnte nicht geladen werden: HTTP {response.status_code}",
            }

        # Debug: log response info
        bot.log(f"Content-Length: {len(response.text)}")

        # Check if response contains any HTML
        if not response.text or "<table" not in response.text.lower():
            bot.log("Response enthält keine Tabellen")
            bot.log(f"Response-Vorschau: {response.text[:500]}")
            return {"success": False, "error": "Seite enthält keine gültigen Daten"}

        soup = BeautifulSoup(response.text, "html.parser")

        # Try different table selectors - more comprehensive
        # 1. Table with color style
        table = soup.find("table", {"style": "color: #c3c3c3;"})
        # 2. Table with class highscore
        if not table:
            table = soup.find("table", {"class": "highscore"})
        # 3. Any table inside div#highscore
        if not table:
            highscore_div = soup.find("div", {"id": "highscore"})
            if highscore_div:
                table = highscore_div.find("table")
        # 4. Any table with tbody that has tr with attack link
        if not table:
            tables = soup.find_all("table")
            for t in tables:
                if t.find("tbody") and t.find(
                    "a", href=lambda x: x and "/fight/?to=" in x
                ):
                    table = t
                    break

        if not table:
            bot.log("Keine Highscore-Tabelle gefunden")
            # Debug: log all tables found
            all_tables = soup.find_all("table")
            bot.log(f"Anzahl Tabellen auf Seite: {len(all_tables)}")
            if all_tables:
                for i, t in enumerate(all_tables):
                    style = t.get("style", "")
                    class_attr = t.get("class", "")
                    rows = len(t.find_all("tr"))
                    bot.log(
                        f"  Tabelle {i}: style={style[:50]}, class={class_attr}, rows={rows}"
                    )
            return {"success": False, "error": "Keine Highscore-Tabelle gefunden"}

        tbody = table.find("tbody")
        if not tbody:
            bot.log("Tabelle hat keinen Body")
            return {"success": False, "error": "Tabelle hat keinen Body"}

        rows = tbody.find_all("tr", {"class": ["odd", "even"]}) or tbody.find_all("tr")
        if not rows:
            bot.log("Keine Spieler-Reihen gefunden")
            return {"success": False, "error": "Keine Spieler-Reihen gefunden"}

        bot.log(f"{len(rows)} Spieler-Reihen gefunden")

        # Find the last row with attackable player (not empty)
        attackable_players = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 6:
                attack_link = cols[5].find(
                    "a", {"href": lambda x: x and "/fight/?to=" in x}
                )
                if attack_link:
                    player_link = cols[1].find("a", {"class": "username"}) or cols[
                        1
                    ].find("a")
                    if player_link:
                        player_name = player_link.get_text(strip=True)
                        if player_name:
                            attackable_players.append(player_name)

        if not attackable_players:
            bot.log("Kein angreifbarer Spieler gefunden")
            return {"success": False, "error": "Kein angreifbarer Spieler gefunden"}

        # Take the last (weakest) player
        player_name = attackable_players[-1]
        bot.log(
            f"Letzter angreifbarer Spieler gefunden: {player_name} (von {len(attackable_players)} Spielern)"
        )
        return {"success": True, "player_name": player_name}
    except Exception as e:
        bot.log(f"Fehler beim Ermitteln des letzten angreifbaren Spielers: {e}")
        import traceback

        bot.log(f"Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}


def start_fight(bot):
    from .parse import parse_header_counters

    try:
        if bot.bottles_running:
            bot.log("Pfandflaschen sammeln läuft - Kampf übersprungen")
            return {
                "success": False,
                "message": "Pfandflaschen sammeln läuft - Kampf nicht möglich",
            }
        bot.log("Starte Kampf...")
        # Check if fight is already running
        if bot.fight_running:
            bot.log("Kampf läuft bereits")
            return {"success": False, "message": "Kampf läuft bereits"}

        # Check if cart needs to be emptied first
        activities = bot.get_activities_data(use_cache=True)
        bottles_status = activities.get("bottles", {})
        if bottles_status.get("pending"):
            bot.log("Einkaufswagen muss zuerst geleert werden...")
            empty_result = empty_bottle_cart(bot)
            if not empty_result.get("success"):
                bot.log("Einkaufswagen konnte nicht geleert werden")
                return {
                    "success": False,
                    "message": "Einkaufswagen konnte nicht geleert werden",
                }

        # Get last attackable player
        player_result = get_last_attackable_player(bot)
        if not player_result.get("success"):
            return {
                "success": False,
                "message": player_result.get("error", "Unbekannter Fehler"),
            }

        player_name = player_result["player_name"]
        bot.log(f"Greife {player_name} an...")

        # Go to fight page for the player
        response = bot.api_get(bot.client, f"/fight/?to={player_name}")
        if response.status_code != 200:
            bot.log(f"Konnte Kampf-Seite nicht laden: HTTP {response.status_code}")
            return {
                "success": False,
                "message": f"Konnte Kampf-Seite nicht laden: HTTP {response.status_code}",
            }

        # Start the fight
        fight_response = bot.api_post(
            bot.client,
            "/fight/attack/",
            data={"f_toid": player_name, "Submit2": "Angriff"},
        )

        if fight_response.status_code == 200:
            # Check multiple possible success indicators from the game response
            success_indicators = [
                "Angriff erfolgreich gestartet",
                "Kampf wurde gestartet",
                "Du kämpfst jetzt gegen",
                "Angriff läuft",
                "counter(",
                "pommerngreif",  # opponent name in response
            ]

            # Also check for notifyme success message
            if (
                '<div id="notifyme"' in fight_response.text
                and "Angriff erfolgreich gestartet" in fight_response.text
            ):
                success_indicators.append("notifyme")

            fight_started = any(
                indicator in fight_response.text for indicator in success_indicators
            )

            if fight_started:
                bot.log(f"Kampf gegen {player_name} gestartet")
                # Set fight running status
                bot.fight_running = True
                # Set estimated fight duration (default 10 min, can be modified by weather)
                from datetime import datetime

                bot.fight_started_at = datetime.now()
                bot.fight_seconds_remaining = 600  # 10 minutes default

                try:
                    counters = parse_header_counters(fight_response.text)
                    bot._update_activity_status(counters)
                    bot._status_cache_time = datetime.now()
                except Exception as e:
                    bot.log(f"Could not parse counters: {e}")
                return {
                    "success": True,
                    "message": f"Kampf gegen {player_name} gestartet",
                    "opponent": player_name,
                }
            else:
                # Even if we don't detect success, the fight might have started
                # Check if response indicates any fight activity
                if "Angriff" in fight_response.text or "Kampf" in fight_response.text:
                    bot.log(
                        f"Kampf gegen {player_name} möglicherweise gestartet (nicht sicher erkannt)"
                    )
                    bot.fight_running = True
                    from datetime import datetime

                    bot.fight_started_at = datetime.now()
                    bot.fight_seconds_remaining = 600
                    return {
                        "success": True,
                        "message": f"Kampf gegen {player_name} gestartet (nicht sicher erkannt)",
                        "opponent": player_name,
                    }
                bot.log(
                    "Kampf konnte nicht gestartet werden - keine Erfolgsindikatoren gefunden"
                )
                bot.log(f"Antwort-Vorschau: {fight_response.text[:200]}")
                return {
                    "success": False,
                    "message": "Kampf konnte nicht gestartet werden",
                }
        else:
            bot.log(f"Kampf-Start fehlgeschlagen: HTTP {fight_response.status_code}")
            return {"success": False, "message": f"HTTP {fight_response.status_code}"}
    except Exception as e:
        error_msg = f"Fehler beim Starten des Kampfes: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def get_fight_status(bot, force_refresh: bool = False):
    try:
        activities = bot.get_activities_data(use_cache=not force_refresh)
        return {"success": True, "fight": activities.get("fight", {})}
    except Exception as e:
        bot.log(f"Fehler beim Abrufen des Kampf-Status: {e}")
        return {"success": False, "error": str(e)}


def cancel_fight(bot):
    from .parse import parse_header_counters

    try:
        bot.log("Breche Kampf ab...")
        # Check if fight is actually running
        if not bot.fight_running:
            bot.log("Kein Kampf läuft")
            return {"success": False, "message": "Kein Kampf läuft"}

        # Send cancel request
        response = bot.api_post(
            bot.client, "/fight/cancel/", data={"cancel_sub": "Angriff abbrechen"}
        )
        if response.status_code == 200:
            try:
                counters = parse_header_counters(response.text)
                bot._update_activity_status(counters)
                bot._status_cache_time = datetime.now()
            except Exception as e:
                bot.log(f"Could not parse counters: {e}")

            if (
                "Kampf abgebrochen" in response.text
                or "Angriff wurde abgebrochen" in response.text
                or "fight/cancel" in str(response.url)
            ):
                bot.log("Kampf abgebrochen")
                return {"success": True, "message": "Kampf abgebrochen"}
            else:
                bot.log("Abbruch möglicherweise fehlgeschlagen")
                return {
                    "success": False,
                    "message": "Abbruch fehlgeschlagen - Status noch aktiv",
                }
        else:
            return {"success": False, "message": f"HTTP {response.status_code}"}
    except Exception as e:
        error_msg = f"Fehler beim Abbrechen des Kampfes: {e}"
        bot.log(error_msg)
        return {"success": False, "message": error_msg}


def auto_drink_before_training(bot, target_promille: float = 3.5):
    from src.constants import (
        PROMILLE_SAFE_TRAINING_MAX,
        PROMILLE_SAFE_TRAINING_MIN,
        PROMILLE_WARNING_THRESHOLD,
    )

    try:
        if target_promille < PROMILLE_SAFE_TRAINING_MIN:
            target_promille = PROMILLE_SAFE_TRAINING_MIN
        elif target_promille > PROMILLE_SAFE_TRAINING_MAX:
            target_promille = PROMILLE_SAFE_TRAINING_MAX
        bot.log(f"Auto-Trinken: Ziel {target_promille:.2f}‰...")
        drinks_data = bot.get_drinks_data()
        current_promille = drinks_data.get("current_promille", 0.0)
        available_drinks = drinks_data.get("drinks", [])
        bot.log(f"Aktuell: {current_promille:.2f}‰")

        if current_promille >= target_promille:
            bot.log(
                f"Promille bereits ausreichend ({current_promille:.2f}‰ >= {target_promille:.2f}‰)"
            )
            return {
                "success": True,
                "message": f"Promille bereits bei {current_promille:.2f}‰",
                "current_promille": current_promille,
                "drank": False,
            }

        if current_promille >= PROMILLE_WARNING_THRESHOLD:
            bot.log(f"Promille zu hoch ({current_promille:.2f}‰), kein Trinken!")
            return {
                "success": False,
                "message": f"Promille zu hoch: {current_promille:.2f}‰",
                "current_promille": current_promille,
                "drank": False,
            }

        needed_promille = target_promille - current_promille
        if needed_promille <= 0:
            bot.log("Bereits am Ziel")
            return {
                "success": True,
                "message": "Bereits am Ziel",
                "current_promille": current_promille,
                "drank": False,
            }

        bot.log(f"Benötigt: +{needed_promille:.2f}‰")

        if not available_drinks:
            bot.log("Keine Getränke im Inventar!")
            return {
                "success": False,
                "message": "Keine Getränke verfügbar",
                "current_promille": current_promille,
                "drank": False,
            }

        strong_drinks = []
        weak_drinks = []
        for drink in available_drinks:
            effect = drink.get("effect", 0.0)
            count = drink.get("count", 0)
            if effect <= 0 or count <= 0:
                continue
            if effect >= 2.0:
                strong_drinks.append(
                    {
                        "name": drink.get("name", "Unbekannt"),
                        "item_id": drink.get("item_id", ""),
                        "promille": drink.get("promille", "0"),
                        "effect": effect,
                        "count": count,
                    }
                )
            else:
                weak_drinks.append(
                    {
                        "name": drink.get("name", "Unbekannt"),
                        "item_id": drink.get("item_id", ""),
                        "promille": drink.get("promille", "0"),
                        "effect": effect,
                        "count": count,
                    }
                )

        strong_drinks.sort(key=lambda d: d["effect"], reverse=True)
        weak_drinks.sort(key=lambda d: d["effect"], reverse=True)

        new_promille = current_promille
        drinks_consumed = []

        if strong_drinks and needed_promille >= 1.0:
            for drink in strong_drinks:
                if new_promille >= target_promille:
                    break
                remaining = target_promille - new_promille
                effect = drink["effect"]
                available = drink["count"]

                needed = min(available, int(remaining / effect))
                if needed == 0 and remaining > 0:
                    needed = 1

                if needed > 0:
                    total_effect = effect * needed
                    if new_promille + total_effect > target_promille:
                        needed = int(remaining / effect)
                        if needed == 0:
                            continue
                        total_effect = effect * needed

                    if new_promille + total_effect > target_promille:
                        continue

                    bot.log(f"Trinke {needed}x {drink['name']} (je {effect}‰)")
                    result = bot.drink(
                        drink["name"], drink["item_id"], drink["promille"], needed
                    )
                    if result.get("success"):
                        new_promille = result.get("new_promille", new_promille)
                        drinks_consumed.append(
                            f"{needed}x {drink['name']} (+{total_effect:.2f}‰)"
                        )
                        bot.log(
                            f"{drink['name']} getrunken: Jetzt bei {new_promille:.2f}‰"
                        )
                        needed_promille = target_promille - new_promille

        if weak_drinks and needed_promille > 0.05:
            for drink in weak_drinks:
                if new_promille >= target_promille:
                    break
                remaining = target_promille - new_promille
                effect = drink["effect"]
                available = drink["count"]

                needed = min(
                    available,
                    int(remaining / effect) + (1 if remaining % effect > 0.05 else 0),
                )

                if needed <= 0:
                    continue

                total_effect = effect * needed
                if new_promille + total_effect > target_promille:
                    needed = int(remaining / effect)
                    if needed == 0:
                        needed = 1
                    total_effect = effect * needed

                if new_promille + total_effect > target_promille:
                    continue

                bot.log(f"Trinke {needed}x {drink['name']} (je {effect}‰)")
                result = bot.drink(
                    drink["name"], drink["item_id"], drink["promille"], needed
                )
                if result.get("success"):
                    new_promille = result.get("new_promille", new_promille)
                    drinks_consumed.append(
                        f"{needed}x {drink['name']} (+{total_effect:.2f}‰)"
                    )
                    bot.log(f"{drink['name']} getrunken: Jetzt bei {new_promille:.2f}‰")
                    needed_promille = target_promille - new_promille

        if drinks_consumed:
            drinks_str = " + ".join(drinks_consumed)
            final_promille = min(new_promille, target_promille)
            bot.log(f"Auto-Trinken erfolgreich: {drinks_str} → {final_promille:.2f}‰")
            return {
                "success": True,
                "message": f"Getrunken: {drinks_str}",
                "current_promille": final_promille,
                "drank": True,
            }
        else:
            bot.log("Kein passendes Getränk gefunden oder bereits am Ziel")
            return {
                "success": True,
                "message": "Bereits am Ziel oder kein passendes Getränk",
                "current_promille": current_promille,
                "drank": False,
            }
    except Exception as e:
        error_msg = f"Fehler beim Auto-Trinken: {e}"
        bot.log(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "current_promille": 0.0,
            "drank": False,
        }
