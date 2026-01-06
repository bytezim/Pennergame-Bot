import re

from bs4 import BeautifulSoup


def parse_header_counters(html: str) -> dict:
    """
    Parse die Counter aus dem Header (Weiterbildung, Kampf, Pfandflaschen)

    Returns:
        dict mit counter0 (skill_seconds), counter1 (fight_seconds), counter2 (bottle_seconds)
    """
    counters = {}

    # Regex pattern für counter(SEKUNDEN, URL) oder counter(SEKUNDEN)
    # counter0 = Weiterbildung, counter1 = Kampf, counter2 = Pfandflaschen

    # Skill counter (counter0)
    skill_match = re.search(r'counter\((\d+)[,"]*/skills/', html)
    if skill_match:
        counters["skill_seconds"] = int(skill_match.group(1))
    else:
        counters["skill_seconds"] = None

    # Fight counter (counter1)
    fight_match = re.search(r'counter\((-?\d+)[,"]*/fight/', html)
    if fight_match:
        counters["fight_seconds"] = int(fight_match.group(1))
    else:
        counters["fight_seconds"] = None

    # Bottles counter (counter2)
    bottles_match = re.search(r'counter\((\d+)[,"]*/activities/', html)
    if bottles_match:
        counters["bottle_seconds"] = int(bottles_match.group(1))
    else:
        counters["bottle_seconds"] = None

    return counters


def parse_promille(html: str) -> float:
    """
    Parse den Promillewert aus dem Header

    Returns:
        float: Promillewert (z.B. 2.50 für 2.50‰)
    """
    soup = BeautifulSoup(html, "html.parser")

    # Suche nach <li class="icon beer">
    beer_li = soup.find("li", class_="icon beer")
    if beer_li:
        # Text enthält z.B. "2.50 ‰" oder "0.00 ‰"
        text = beer_li.get_text(strip=True)
        # Extrahiere die Zahl vor dem ‰
        match = re.search(r"([\d.]+)\s*‰", text)
        if match:
            return float(match.group(1))

    return 0.0


def parse_bottle_price(html: str) -> int:
    """
    Parse den aktuellen Pfandflaschenpreis aus dem Header

    Returns:
        int: Preis in Cent (z.B. 21, 24, etc.)
    """
    soup = BeautifulSoup(html, "html.parser")

    # Suche nach <li class="icon bottle">
    bottle_li = soup.find("li", class_="icon bottle")
    if bottle_li:
        # Text enthält z.B. "21 Cent" oder "24 Cent"
        text = bottle_li.get_text(strip=True)
        # Extrahiere die Zahl vor "Cent"
        match = re.search(r"(\d+)\s*Cent", text)
        if match:
            return int(match.group(1))

    return 0


def parse_money(html: str) -> float:
    """
    Parse den aktuellen Geldbetrag aus dem Header

    Returns:
        float: Geldbetrag in Euro (z.B. 428200.98)
    """
    soup = BeautifulSoup(html, "html.parser")

    # Suche nach <li class="icon money">
    money_li = soup.find("li", class_="icon money")
    if money_li:
        # Text enthält z.B. "€428.200,98" oder "€1.234,56"
        text = money_li.get_text(strip=True)
        # Extrahiere die Zahl nach € (Format: €428.200,98)
        match = re.search(r"€([\d.,]+)", text)
        if match:
            money_str = match.group(1)
            # Entferne Tausender-Punkte und ersetze Komma durch Punkt
            money_str = money_str.replace(".", "").replace(",", ".")
            try:
                return float(money_str)
            except ValueError:
                return 0.0

    return 0.0


def parse_bottle_count(html: str) -> int:
    """
    Parse die Anzahl verfügbarer Pfandflaschen aus /stock/bottle/

    Returns:
        int: Anzahl der Flaschen (aus <input name="max" value="...">)
    """
    soup = BeautifulSoup(html, "html.parser")

    max_input = soup.find("input", {"name": "max"})
    if max_input:
        try:
            return int(max_input.get("value", 0))
        except (ValueError, TypeError):
            return 0

    return 0


def parse_overview(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    penner = {}

    # Username, ID, Location, Rank, Points
    profile_data = soup.find("div", class_="profile-data")
    if profile_data:
        try:
            user_name_span = profile_data.find("span", class_="user_name")
            if user_name_span:
                penner["username"] = user_name_span.text.strip()
            
            el2_spans = profile_data.find_all("span", class_="el2")
            if len(el2_spans) >= 4:
                penner["user_id"] = int(el2_spans[0].text.strip())
                penner["location"] = el2_spans[1].text.strip()
                penner["rank"] = int(el2_spans[2].text.strip())
                penner["points"] = int(el2_spans[3].text.strip())
        except (ValueError, IndexError, AttributeError) as e:
            print(f"Warning: Failed to parse profile data: {e}")

    # Money, Promille, ATT, DEF, Cleanliness, Status
    summary = soup.find("div", id="summary")
    if summary:
        status_ov = summary.find("div", class_="status_ov")
        if status_ov:
            # Status message kann verschiedene Promille-Klassen haben
            status_msg_div = status_ov.find("div", class_="status_msg")
            if status_msg_div:
                status_span = (
                    status_msg_div.find("span", class_="promille_rot")
                    or status_msg_div.find("span", class_="promille_grun")
                    or status_msg_div.find("span", class_="promille_gelb")
                )
                if status_span:
                    penner["status_message"] = status_span.text.strip()
                else:
                    penner["status_message"] = status_msg_div.get_text(strip=True)

            status_list_ul = status_ov.find("ul", class_="status")
            if status_list_ul:
                status_list = status_list_ul.find_all("li")
                try:
                    if len(status_list) >= 1:
                        rank_span = status_list[0].find_all("span")
                        if len(rank_span) >= 2:
                            penner["rank"] = int(rank_span[1].text.strip().replace(".", ""))
                    if len(status_list) >= 2:
                        money_span = status_list[1].find_all("span")
                        if len(money_span) >= 2:
                            penner["money"] = money_span[1].text.strip()
                except (ValueError, IndexError, AttributeError) as e:
                    print(f"Warning: Failed to parse status list: {e}")

            # Parse Promille - robuster mit Fallback (suche nach allen Promille-Klassen)
            try:
                promille_li = None
                if status_list and len(status_list) >= 3:
                    promille_li = status_list[2]
                
                if promille_li:
                    # Suche nach span mit promille_rot, promille_grun oder promille_gelb
                    promille_span = (
                        promille_li.find("span", class_="promille_rot")
                        or promille_li.find("span", class_="promille_grun")
                        or promille_li.find("span", class_="promille_gelb")
                    )
                    if promille_span:
                        promille_text = promille_span.text.strip()
                        # Entferne alle möglichen Varianten von Promille-Zeichen
                        promille_text = (
                            promille_text.replace("&permil;", "")
                            .replace("‰", "")
                            .replace(",", ".")
                            .strip()
                        )
                        penner["promille"] = float(promille_text)
                    else:
                        # Fallback: Versuche aus dem gesamten Text zu extrahieren
                        text = promille_li.get_text(strip=True)
                        match = re.search(r"([\d,\.]+)\s*‰", text)
                        if match:
                            penner["promille"] = float(match.group(1).replace(",", "."))
                        else:
                            penner["promille"] = 0.0
                else:
                    penner["promille"] = 0.0
            except (ValueError, IndexError, AttributeError) as e:
                print(f"Warning: Failed to parse promille: {e}")
                penner["promille"] = 0.0

            try:
                if status_list and len(status_list) >= 4:
                    att_span = status_list[3].find("span", class_="att")
                    if att_span:
                        penner["att"] = int(att_span.text.strip())
                if status_list and len(status_list) >= 5:
                    def_span = status_list[4].find("span", class_="def")
                    if def_span:
                        penner["deff"] = int(def_span.text.strip())
            except (ValueError, IndexError, AttributeError) as e:
                print(f"Warning: Failed to parse att/def: {e}")

            try:
                processbar_clean = status_ov.find("div", class_="processbar_clean")
                if processbar_clean:
                    style = processbar_clean.get("style")
                    if style:
                        match = re.search(r"width:\s*(\d+)", style)
                        if match:
                            penner["cleanliness"] = int(match.group(1))
            except (ValueError, IndexError, AttributeError) as e:
                print(f"Warning: Failed to parse cleanliness: {e}")

            # Daily task
            penner["daily_task_done"] = "noch nicht erledigt" not in status_ov.text

    # Plunder
    plunder = []
    plunder_table = soup.find("table")
    if plunder_table:
        slots = ["Allgemein", "Bildung", "Schmuck"]
        try:
            for idx, td in enumerate(plunder_table.find_all("td", class_="ztipfull")):
                name_tag = td.find("strong")
                if name_tag:
                    name = name_tag.text.strip()
                    plunder.append({"slot": slots[idx] if idx < len(slots) else f"Slot {idx}", "name": name})
        except (ValueError, IndexError, AttributeError) as e:
            print(f"Warning: Failed to parse plunder: {e}")
    penner["plunder"] = plunder

    # Container
    container_div = soup.find("h4", string="Container")
    if container_div:
        ul = container_div.find_next("ul")
        if ul:
            items = ul.find_all("li")
            try:
                if len(items) >= 1:
                    container_text = items[0].text
                    if ":" in container_text:
                        parts = container_text.split(":")
                        penner["container_capacity"] = parts[0].split("Gefüllt")[0].strip() if "Gefüllt" in container_text else container_text.strip()
                    
                    processbar = items[0].find("div", class_="processbar")
                    if processbar:
                        style = processbar.get("style")
                        if style:
                            match = re.search(r"width:\s*(\d+)", style)
                            if match:
                                penner["container_filled_percent"] = int(match.group(1))
                            else:
                                penner["container_filled_percent"] = 0
                        else:
                            penner["container_filled_percent"] = 0
                    else:
                        penner["container_filled_percent"] = 0
                
                if len(items) >= 2:
                    strong = items[1].find("strong")
                    if strong:
                        penner["container_donors"] = int(strong.text.strip())
                
                if len(items) >= 3:
                    penner["container_total_donations"] = items[2].find("strong").text.strip() if items[2].find("strong") else "0"
                
                if len(items) >= 4:
                    text = items[3].text
                    match = re.search(r"(\d+)", text)
                    if match:
                        penner["container_donations_today"] = int(match.group(1))
                
                if len(items) >= 5:
                    input_elem = items[4].find("input")
                    if input_elem:
                        penner["container_ref_link"] = input_elem.get("value", "")
            except (ValueError, IndexError, AttributeError) as e:
                print(f"Warning: Failed to parse container: {e}")

    # Weapon
    weapon_div = soup.find("h4", string=lambda s: s and "Waffe" in s)
    if weapon_div:
        ul = weapon_div.find_next("ul")
        if ul:
            items = ul.find_all("li")
            try:
                if items:
                    penner["weapon_name"] = items[0].text.strip()
                    # Try to extract ATT bonus from second li
                    if len(items) >= 2:
                        att_text = items[1].text.strip()
                        att_val = int("".join(filter(str.isdigit, att_text)))
                        penner["weapon_att"] = att_val
                    else:
                        penner["weapon_att"] = None
                else:
                    penner["weapon_name"] = None
                    penner["weapon_att"] = None
            except (ValueError, IndexError, AttributeError) as e:
                print(f"Warning: Failed to parse weapon: {e}")
                penner["weapon_name"] = None
                penner["weapon_att"] = None

    # Home
    home_div = soup.find("h4", string=lambda s: s and "Eigenheim" in s)
    if home_div:
        ul = home_div.find_next("ul")
        if ul:
            items = ul.find_all("li")
            try:
                if items:
                    penner["home_name"] = items[0].text.strip()
                    if len(items) >= 2:
                        def_text = items[1].text.strip()
                        def_val = int("".join(filter(str.isdigit, def_text)))
                        penner["home_def"] = def_val
                    else:
                        penner["home_def"] = None
                else:
                    penner["home_name"] = None
                    penner["home_def"] = None
            except (ValueError, IndexError, AttributeError) as e:
                print(f"Warning: Failed to parse home: {e}")
                penner["home_name"] = None
                penner["home_def"] = None

    # Instrument
    instr_div = soup.find("h4", string=lambda s: s and "Instrument" in s)
    if instr_div:
        ul = instr_div.find_next("ul")
        if ul:
            items = ul.find_all("li")
            try:
                if items:
                    penner["instrument_name"] = items[0].text.strip()
                    income = None
                    for li in items:
                        if "am Tag" in li.text:
                            income = li.text.strip()
                            break
                    penner["instrument_income_per_day"] = income
                    payout = None
                    for li in items:
                        form = li.find("form")
                        if form:
                            input_elem = form.find("input", {"type": "submit"})
                            if input_elem and input_elem.has_attr("value"):
                                payout = input_elem["value"].strip()
                                break
                    penner["instrument_payout"] = payout
                else:
                    penner["instrument_name"] = None
                    penner["instrument_income_per_day"] = None
                    penner["instrument_payout"] = None
            except (ValueError, IndexError, AttributeError) as e:
                print(f"Warning: Failed to parse instrument: {e}")
                penner["instrument_name"] = None
                penner["instrument_income_per_day"] = None
                penner["instrument_payout"] = None

    # Schnorrplatz
    schnorr_div = soup.find("h4", string=lambda s: s and "Schnorrplatz" in s)
    if schnorr_div:
        ul = schnorr_div.find_next("ul")
        if ul:
            items = ul.find_all("li")
            try:
                if items:
                    penner["schnorrplatz_name"] = items[0].text.strip()
                    income = None
                    for li in items:
                        if "je Spende" in li.text:
                            income = li.text.strip()
                            break
                    penner["schnorrplatz_income_per_donation"] = income
                else:
                    penner["schnorrplatz_name"] = None
                    penner["schnorrplatz_income_per_donation"] = None
            except (ValueError, IndexError, AttributeError) as e:
                print(f"Warning: Failed to parse schnorrplatz: {e}")
                penner["schnorrplatz_name"] = None
                penner["schnorrplatz_income_per_donation"] = None

    # Pet
    pet_div = soup.find("h4", string=lambda s: s and "Begleiter" in s)
    if pet_div:
        ul = pet_div.find_next("ul")
        if ul:
            items = ul.find_all("li")
            try:
                if items:
                    penner["pet_name"] = items[0].text.strip()
                    att_def = None
                    for li in items:
                        if "Angriff/Verteidigung" in li.text:
                            att_def = li.text.strip()
                            break
                    if att_def:
                        try:
                            parts = att_def.split(":")[1].split("/")
                            penner["pet_attack"] = int(parts[0].strip())
                            penner["pet_defense"] = int(parts[1].strip())
                        except Exception:
                            penner["pet_attack"] = None
                            penner["pet_defense"] = None
                    else:
                        penner["pet_attack"] = None
                        penner["pet_defense"] = None
                    tricks = None
                    for li in items:
                        if "Kunstst" in li.text:
                            try:
                                tricks = int("".join(filter(str.isdigit, li.text)))
                            except Exception:
                                tricks = None
                            break
                    penner["pet_tricks"] = tricks
                else:
                    penner["pet_name"] = None
                    penner["pet_attack"] = None
                    penner["pet_defense"] = None
                    penner["pet_tricks"] = None
            except (ValueError, IndexError, AttributeError) as e:
                print(f"Warning: Failed to parse pet: {e}")
                penner["pet_name"] = None
                penner["pet_attack"] = None
                penner["pet_defense"] = None
                penner["pet_tricks"] = None

    return penner


def parse_activities(html: str) -> dict:
    """
    Parse die /activities/ Seite (Pfandflaschen sammeln, Konzentration, Verbrechen)

    Returns:
        dict mit allen Activity-Infos
    """
    soup = BeautifulSoup(html, "html.parser")
    activities = {}

    bottles = {}

    bottles["pending"] = "bottlecollect_pending" in html
    bottles["collecting"] = "Du bist auf Pfandflaschensuche" in html

    bottles_table = None
    for table in soup.find_all("table", class_="cbox"):
        tiername = table.find("span", class_="tiername")
        if tiername and "Pfandflaschen" in tiername.text:
            bottles_table = table
            break

    if bottles_table:
        for td in bottles_table.find_all("td"):
            if "Geld bisher erwirtschaftet" in td.text:
                try:
                    money_match = re.search(r"€([\d.,]+)", td.text)
                    if money_match:
                        bottles["total_earned"] = money_match.group(1)
                except Exception:
                    pass

        gewinn_span = soup.find("span", id="gewinn")
        if gewinn_span:
            text = gewinn_span.text.strip()
            bottles["expected_profit"] = text if text else None

        flaschen_span = soup.find("span", id="flaschen")
        if flaschen_span:
            text = flaschen_span.text.strip()
            bottles["expected_bottles"] = text if text else None

        time_select = bottles_table.find("select", {"name": "time"})
        if time_select:
            selected = time_select.find("option", selected=True)
            if selected:
                bottles["current_time"] = selected.get("value")

        if bottles["collecting"]:
            counter_match = re.search(r"counter\((\d+)\)", html)
            if counter_match:
                bottles["seconds_remaining"] = int(counter_match.group(1))

            end_match = re.search(r"var end = (\d+);", html)
            if end_match:
                bottles["end_timestamp"] = int(end_match.group(1))

        for tr in bottles_table.find_all("tr"):
            if "Du hast zuletzt" in tr.text:
                link = tr.find("a")
                if link:
                    bottles["last_found"] = link.text.strip()
                break

        for tr in bottles_table.find_all("tr"):
            if "Missionsplunder gefunden" in tr.text:
                try:
                    amount_match = re.search(r"(\d+)\s*x\s*<strong>", str(tr))
                    if amount_match:
                        bottles["mission_plunder_amount"] = int(amount_match.group(1))

                    link = tr.find("a", href="/stock/plunder/")
                    if link:
                        bottles["mission_plunder_name"] = link.text.strip()
                except Exception:
                    pass
                break

    activities["bottles"] = bottles

    concentration = {}

    konz_table = None
    for table in soup.find_all("table", class_="cbox"):
        tiername = table.find("span", class_="tiername")
        if tiername and "Konzentrieren" in tiername.text:
            konz_table = table
            break

    if konz_table:
        skill_perc = konz_table.find("span", id="skill_perc")
        if skill_perc:
            concentration["boost_percent"] = skill_perc.text.strip()

        concentration["active"] = "Du konzentrierst dich gerade" in konz_table.text

        if concentration["active"]:
            if (
                "Pfandflaschensammeln" in konz_table.text
                and "Nebenbeschäftigung:" in konz_table.text
            ):
                if "<strong>Pfandflaschensammeln</strong>" in str(konz_table):
                    concentration["mode"] = "Pfandflaschensammeln"
                    concentration["mode_value"] = "3"
                elif "<strong>Kämpfen</strong>" in str(konz_table):
                    concentration["mode"] = "Kämpfen"
                    concentration["mode_value"] = "2"
                else:
                    concentration["mode"] = "Keine"
                    concentration["mode_value"] = "1"
            elif (
                "Kämpfen" in konz_table.text
                and "Nebenbeschäftigung:" in konz_table.text
            ):
                if "<strong>Kämpfen</strong>" in str(konz_table):
                    concentration["mode"] = "Kämpfen"
                    concentration["mode_value"] = "2"
                else:
                    concentration["mode"] = "Keine"
                    concentration["mode_value"] = "1"
            else:
                concentration["mode"] = "Keine"
                concentration["mode_value"] = "1"
        else:
            mode_select = konz_table.find("select", {"name": "mode"})
            if mode_select:
                selected = mode_select.find("option", selected=True)
                if selected:
                    concentration["mode"] = selected.text.strip()
                    concentration["mode_value"] = selected.get("value", "1")

    activities["concentration"] = concentration

    crime = {}

    crime_table = None
    for table in soup.find_all("table", class_="cbox"):
        tiername = table.find("span", class_="tiername")
        if tiername and "Verbrechen" in tiername.text:
            crime_table = table
            break

    if crime_table:
        button = crime_table.find("button", class_="grey_button")
        crime["available"] = button is not None

    activities["crime"] = crime

    overview = {}

    overview_table = None
    for table in soup.find_all("table", class_="cbox"):
        tiername = table.find("span", class_="tiername")
        if tiername and "Beschäftigungen" in tiername.text:
            overview_table = table
            break

    if overview_table:
        for td in overview_table.find_all("td"):
            text = td.text

            if "Gesch.:" in text:
                try:
                    gesch_match = re.search(r"Gesch\.: (\d+)", text)
                    if gesch_match:
                        overview["geschicklichkeit"] = int(gesch_match.group(1))
                    bonus_match = re.search(r"\(\+([\d.]+)%\)", text)
                    if bonus_match:
                        overview["geschicklichkeit_bonus"] = bonus_match.group(1)
                except Exception:
                    pass

            if "Sauberkeit:" in text:
                try:
                    clean_match = re.search(r"Sauberkeit: (\d+)", text)
                    if clean_match:
                        overview["sauberkeit"] = int(clean_match.group(1))
                except Exception:
                    pass

            if "Stadtteil:" in text:
                try:
                    district_match = re.search(r"Stadtteil: (.+)$", text)
                    if district_match:
                        overview["stadtteil"] = district_match.group(1).strip()
                except Exception:
                    pass

    activities["overview"] = overview

    return activities


def parse_skills(html: str) -> dict:
    """
    Parse die /skills/ Seite für Weiterbildungen (Angriff, Verteidigung, Geschicklichkeit)

    Returns:
        dict mit running_skill und available_skills (att, def, agi)
    """
    soup = BeautifulSoup(html, "html.parser")
    skills = {}

    # Prüfe ob eine Weiterbildung läuft
    running_box = soup.find("div", class_="box_main_small")
    if running_box and "Es läuft bereits eine Weiterbildung" in running_box.text:
        running = {}

        # Skill-Name (z.B. "Geschicklichkeit", "Angriff", "Verteidigung")
        skill_span = running_box.find("span", class_="style_skill")
        if skill_span:
            skill_text = skill_span.text.strip()
            running["name"] = skill_text

            # Map zu skill_type
            if "Geschick" in skill_text:
                running["skill_type"] = "agi"
            elif "Angriff" in skill_text:
                running["skill_type"] = "att"
            elif "Verteidigung" in skill_text:
                running["skill_type"] = "def"
            else:
                running["skill_type"] = None

        # Level (z.B. "[Stufe 47]")
        level_match = re.search(r"\[Stufe (\d+)\]", running_box.text)
        if level_match:
            running["level"] = int(level_match.group(1))

        # Verbleibende Zeit in Sekunden (aus counter JavaScript)
        counter_match = re.search(r"counter\((\d+)\)", str(running_box))
        if counter_match:
            running["seconds_remaining"] = int(counter_match.group(1))

        # End timestamp
        end_match = re.search(r"var end = (\d+);", html)
        if end_match:
            running["end_timestamp"] = int(end_match.group(1))

        # Start timestamp
        start_match = re.search(r"var start = (\d+);", html)
        if start_match:
            running["start_timestamp"] = int(start_match.group(1))

        # Voraussichtliche Punkte
        points_match = re.search(r"Voraussichtlich (\d+) Punkte", running_box.text)
        if points_match:
            running["expected_points"] = int(points_match.group(1))

        skills["running_skill"] = running
    else:
        skills["running_skill"] = None

    # Parse verfügbare Skills (Angriff, Verteidigung, Geschicklichkeit)
    available = {}

    # Alle Skill-Tabellen durchgehen
    for table in soup.find_all("table", class_="cbox"):
        skill_name_elem = table.find("strong")
        if not skill_name_elem:
            continue

        skill_name = skill_name_elem.text.strip()

        # Nur die drei Kampfstärken beachten
        if skill_name not in ["Angriff", "Verteidigung", "Geschicklichkeit"]:
            continue

        skill_data = {}
        skill_data["display_name"] = skill_name

        # Skill-Typ
        if skill_name == "Angriff":
            skill_type = "att"
        elif skill_name == "Verteidigung":
            skill_type = "def"
        elif skill_name == "Geschicklichkeit":
            skill_type = "agi"
        else:
            continue

        skill_data["skill_type"] = skill_type

        # Aktuelles Level / Max Level
        level_td = table.find("td", string=re.compile(r"\d+/"))
        if level_td:
            level_text = level_td.text.strip()
            level_match = re.search(r"(\d+)/(.+)", level_text)
            if level_match:
                skill_data["current_level"] = int(level_match.group(1))
                max_level_str = level_match.group(2).strip()
                if "∞" in max_level_str:
                    skill_data["max_level"] = None  # Unbegrenzt
                else:
                    try:
                        skill_data["max_level"] = int(max_level_str)
                    except:
                        skill_data["max_level"] = None

        # Kosten für nächste Stufe
        cost_match = re.search(r"Nächste Stufe: €([\d.,]+)", table.text)
        if cost_match:
            skill_data["next_level_cost"] = cost_match.group(1)

        # Dauer
        duration_match = re.search(r"Dauer:\s*([\d:]+)", table.text)
        if duration_match:
            skill_data["duration"] = duration_match.group(1).strip()

        # Button vorhanden?
        button = table.find("input", {"type": "button", "value": "Weiterbilden"})
        skill_data["can_start"] = button is not None

        available[skill_type] = skill_data

    skills["available_skills"] = available

    return skills


def parse_drinks(html: str) -> dict:
    """
    Parse die verfügbaren Getränke aus dem Inventar (/stock/)

    Returns:
        dict: {
            "drinks": [
                {
                    "name": str,  # z.B. "Bier", "Wodka"
                    "item_id": str,  # ID für den POST request
                    "count": int,  # Anzahl im Inventar
                    "promille": str,  # Promillewert als String (z.B. "35", "250")
                    "effect": float  # Wirkung in ‰ (z.B. 0.35, 2.50)
                }
            ]
        }
    """
    soup = BeautifulSoup(html, "html.parser")
    drinks = []

    # Suche alle Forms mit action="/stock/foodstuffs/use/"
    forms = soup.find_all("form", action="/stock/foodstuffs/use/")

    for form in forms:
        drink = {}

        # Parse hidden inputs
        item_input = form.find("input", {"name": "item"})
        if not item_input:
            continue
        drink["name"] = item_input.get("value", "")

        id_input = form.find("input", {"name": "id"})
        if id_input:
            drink["item_id"] = id_input.get("value", "")

        promille_input = form.find("input", {"name": "promille"})
        if promille_input:
            drink["promille"] = promille_input.get("value", "")
            # Berechne den Float-Wert (z.B. "250" -> 2.50)
            try:
                drink["effect"] = float(drink["promille"]) / 100.0
            except:
                drink["effect"] = 0.0

        # Parse Anzahl aus dem lager_* hidden field (am zuverlässigsten)
        # z.B. <input type="hidden" id="lager_Bier" value="9984">
        lager_input = form.find("input", {"id": f"lager_{drink['name']}"})
        if lager_input:
            try:
                drink["count"] = int(lager_input.get("value", "0"))
            except (ValueError, TypeError):
                drink["count"] = 0
        else:
            drink["count"] = 0

        if drink.get("name") and drink.get("item_id"):
            drinks.append(drink)

    return {"drinks": drinks}


def parse_food(html: str) -> dict:
    """
    Parse verfügbares Essen aus der /stock/foodstuffs/food/ Seite

    Returns:
        dict: {
            "food": [
                {
                    "name": str,  # z.B. "Brot", "Currywurst", "Hamburger"
                    "item_id": str,  # ID für den POST request
                    "count": int,  # Anzahl im Inventar
                    "promille": str,  # Promillewert als String (z.B. "-35", "-100", "-200")
                    "effect": float  # Wirkung in ‰ (z.B. -0.35, -1.00, -2.00)
                }
            ]
        }
    """
    soup = BeautifulSoup(html, "html.parser")
    food_items = []

    # Suche alle Forms mit action="/stock/foodstuffs/use/"
    forms = soup.find_all("form", action="/stock/foodstuffs/use/")

    for form in forms:
        food = {}

        # Parse hidden inputs
        item_input = form.find("input", {"name": "item"})
        if not item_input:
            continue
        food["name"] = item_input.get("value", "")

        id_input = form.find("input", {"name": "id"})
        if id_input:
            food["item_id"] = id_input.get("value", "")

        promille_input = form.find("input", {"name": "promille"})
        if promille_input:
            food["promille"] = promille_input.get("value", "")
            # Berechne den Float-Wert (z.B. "-35" -> -0.35, "-200" -> -2.00)
            try:
                food["effect"] = float(food["promille"]) / 100.0
            except:
                food["effect"] = 0.0

        # Parse Anzahl aus dem lager_* hidden field
        # z.B. <input type="hidden" id="lager_Brot" value="19">
        lager_input = form.find("input", {"id": f"lager_{food['name']}"})
        if lager_input:
            try:
                food["count"] = int(lager_input.get("value", "0"))
            except (ValueError, TypeError):
                food["count"] = 0
        else:
            food["count"] = 0

        if food.get("name") and food.get("item_id") and food.get("effect", 0) < 0:
            # Nur Essen mit negativem Promille-Effekt
            food_items.append(food)

    return {"food": food_items}
