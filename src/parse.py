import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def parse_header_counters(html: str) -> dict:
    counters = {}
    skill_match = re.search('counter\\((\\d+)[,"]*/skills/', html)
    if skill_match:
        counters["skill_seconds"] = int(skill_match.group(1))
    else:
        counters["skill_seconds"] = None
    fight_match = re.search('counter\\((-?\\d+)[,"]*/fight/', html)
    if fight_match:
        counters["fight_seconds"] = int(fight_match.group(1))
    else:
        counters["fight_seconds"] = None
    bottles_match = re.search('counter\\((\\d+)[,"]*/activities/', html)
    if bottles_match:
        counters["bottle_seconds"] = int(bottles_match.group(1))
    else:
        counters["bottle_seconds"] = None
    return counters


def parse_promille(html: str) -> float:
    soup = BeautifulSoup(html, "html.parser")
    beer_li = soup.find("li", class_="icon beer")
    if beer_li:
        text = beer_li.get_text(strip=True)
        match = re.search("([\\d.]+)\\s*‰", text)
        if match:
            return float(match.group(1))
    return 0.0


def parse_bottle_price(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    bottle_li = soup.find("li", class_="icon bottle")
    if bottle_li:
        text = bottle_li.get_text(strip=True)
        match = re.search("(\\d+)\\s*Cent", text)
        if match:
            return int(match.group(1))
    return 0


def parse_money(html: str) -> float:
    soup = BeautifulSoup(html, "html.parser")
    money_li = soup.find("li", class_="icon money")
    if money_li:
        text = money_li.get_text(strip=True)
        match = re.search("€([\\d.,]+)", text)
        if match:
            money_str = match.group(1)
            money_str = money_str.replace(".", "").replace(",", ".")
            try:
                return float(money_str)
            except ValueError:
                return 0.0
    return 0.0


def parse_bottle_count(html: str) -> int:
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
            else:
                logger.warning("Profile data not found - maybe not logged in")
                return {}
        except (ValueError, IndexError, AttributeError) as e:
            logger.warning("Failed to parse profile data: %s", e)
            return {}
    summary = soup.find("div", id="summary")
    if summary:
        status_ov = summary.find("div", class_="status_ov")
        if status_ov:
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
            status_list = status_list_ul.find_all("li") if status_list_ul else []
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
                logger.warning("Failed to parse status list: %s", e)
            try:
                promille_li = None
                if status_list and len(status_list) >= 3:
                    promille_li = status_list[2]
                if promille_li:
                    promille_span = (
                        promille_li.find("span", class_="promille_rot")
                        or promille_li.find("span", class_="promille_grun")
                        or promille_li.find("span", class_="promille_gelb")
                    )
                    if promille_span:
                        promille_text = promille_span.text.strip()
                        promille_text = (
                            promille_text.replace("&permil;", "")
                            .replace("‰", "")
                            .replace(",", ".")
                            .strip()
                        )
                        penner["promille"] = float(promille_text)
                    else:
                        text = promille_li.get_text(strip=True)
                        match = re.search("([\\d,\\.]+)\\s*‰", text)
                        if match:
                            penner["promille"] = float(match.group(1).replace(",", "."))
                        else:
                            penner["promille"] = 0.0
                else:
                    penner["promille"] = 0.0
            except (ValueError, IndexError, AttributeError) as e:
                logger.warning("Failed to parse promille: %s", e)
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
                logger.warning("Failed to parse att/def: %s", e)
            try:
                processbar_clean = status_ov.find("div", class_="processbar_clean")
                if processbar_clean:
                    style = processbar_clean.get("style")
                    if style:
                        match = re.search("width:\\s*(\\d+)", style)
                        if match:
                            penner["cleanliness"] = int(match.group(1))
            except (ValueError, IndexError, AttributeError) as e:
                logger.warning("Failed to parse cleanliness: %s", e)
            penner["daily_task_done"] = "noch nicht erledigt" not in status_ov.text
    plunder = []
    plunder_table = soup.find("table")
    if plunder_table:
        slots = ["Allgemein", "Bildung", "Schmuck"]
        try:
            for idx, td in enumerate(plunder_table.find_all("td", class_="ztipfull")):
                name_tag = td.find("strong")
                if name_tag:
                    name = name_tag.text.strip()
                    plunder.append(
                        {
                            "slot": slots[idx] if idx < len(slots) else f"Slot {idx}",
                            "name": name,
                        }
                    )
        except (ValueError, IndexError, AttributeError) as e:
            logger.warning("Failed to parse plunder: %s", e)
    penner["plunder"] = plunder
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
                        penner["container_capacity"] = (
                            parts[0].split("Gefüllt")[0].strip()
                            if "Gefüllt" in container_text
                            else container_text.strip()
                        )
                    processbar = items[0].find("div", class_="processbar")
                    if processbar:
                        style = processbar.get("style")
                        if style:
                            match = re.search("width:\\s*(\\d+)", style)
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
                    penner["container_total_donations"] = (
                        items[2].find("strong").text.strip()
                        if items[2].find("strong")
                        else "0"
                    )
                if len(items) >= 4:
                    text = items[3].text
                    match = re.search("(\\d+)", text)
                    if match:
                        penner["container_donations_today"] = int(match.group(1))
                if len(items) >= 5:
                    input_elem = items[4].find("input")
                    if input_elem:
                        penner["container_ref_link"] = input_elem.get("value", "")
            except (ValueError, IndexError, AttributeError) as e:
                logger.warning("Failed to parse container: %s", e)
    weapon_div = soup.find("h4", string=lambda s: s and "Waffe" in s)
    if weapon_div:
        ul = weapon_div.find_next("ul")
        if ul:
            items = ul.find_all("li")
            try:
                if items:
                    penner["weapon_name"] = items[0].text.strip()
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
                logger.warning("Failed to parse weapon: %s", e)
                penner["weapon_name"] = None
                penner["weapon_att"] = None
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
                logger.warning("Failed to parse home: %s", e)
                penner["home_name"] = None
                penner["home_def"] = None
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
                logger.warning("Failed to parse instrument: %s", e)
                penner["instrument_name"] = None
                penner["instrument_income_per_day"] = None
                penner["instrument_payout"] = None
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
                logger.warning("Failed to parse schnorrplatz: %s", e)
                penner["schnorrplatz_name"] = None
                penner["schnorrplatz_income_per_donation"] = None
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
                logger.warning("Failed to parse pet: %s", e)
                penner["pet_name"] = None
                penner["pet_attack"] = None
                penner["pet_defense"] = None
                penner["pet_tricks"] = None
    return penner


def parse_activities(html: str) -> dict:
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
                    money_match = re.search("€([\\d.,]+)", td.text)
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
            counter_match = re.search("counter\\((\\d+)\\)", html)
            if counter_match:
                bottles["seconds_remaining"] = int(counter_match.group(1))
            end_match = re.search("var end = (\\d+);", html)
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
                    amount_match = re.search("(\\d+)\\s*x\\s*<strong>", str(tr))
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
                    gesch_match = re.search("Gesch\\.: (\\d+)", text)
                    if gesch_match:
                        overview["geschicklichkeit"] = int(gesch_match.group(1))
                    bonus_match = re.search("\\(\\+([\\d.]+)%\\)", text)
                    if bonus_match:
                        overview["geschicklichkeit_bonus"] = bonus_match.group(1)
                except Exception:
                    pass
            if "Sauberkeit:" in text:
                try:
                    clean_match = re.search("Sauberkeit: (\\d+)", text)
                    if clean_match:
                        overview["sauberkeit"] = int(clean_match.group(1))
                except Exception:
                    pass
            if "Stadtteil:" in text:
                try:
                    district_match = re.search("Stadtteil: (.+)$", text)
                    if district_match:
                        overview["stadtteil"] = district_match.group(1).strip()
                except Exception:
                    pass
    activities["overview"] = overview
    fight = {}
    fight_match = re.search(r'counter\((\d+),"/fight/"\)', html)
    if fight_match:
        fight["running"] = True
        fight["seconds_remaining"] = int(fight_match.group(1))
    else:
        fight["running"] = False
        fight["seconds_remaining"] = 0
    activities["fight"] = fight
    return activities


def parse_skills(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    skills = {}
    running_box = soup.find("div", class_="box_main_small")
    if running_box and "Es läuft bereits eine Weiterbildung" in running_box.text:
        running = {}
        skill_span = running_box.find("span", class_="style_skill")
        if skill_span:
            skill_text = skill_span.text.strip()
            running["name"] = skill_text
            if "Geschick" in skill_text:
                running["skill_type"] = "agi"
            elif "Angriff" in skill_text:
                running["skill_type"] = "att"
            elif "Verteidigung" in skill_text:
                running["skill_type"] = "def"
            else:
                running["skill_type"] = None
        level_match = re.search("\\[Stufe (\\d+)\\]", running_box.text)
        if level_match:
            running["level"] = int(level_match.group(1))
        counter_match = re.search("counter\\((\\d+)\\)", str(running_box))
        if counter_match:
            running["seconds_remaining"] = int(counter_match.group(1))
        end_match = re.search("var end = (\\d+);", html)
        if end_match:
            running["end_timestamp"] = int(end_match.group(1))
        start_match = re.search("var start = (\\d+);", html)
        if start_match:
            running["start_timestamp"] = int(start_match.group(1))
        points_match = re.search("Voraussichtlich (\\d+) Punkte", running_box.text)
        if points_match:
            running["expected_points"] = int(points_match.group(1))
        skills["running_skill"] = running
    else:
        skills["running_skill"] = None
    available = {}
    for table in soup.find_all("table", class_="cbox"):
        skill_name_elem = table.find("strong")
        if not skill_name_elem:
            continue
        skill_name = skill_name_elem.text.strip()
        if skill_name not in ["Angriff", "Verteidigung", "Geschicklichkeit"]:
            continue
        skill_data = {}
        skill_data["display_name"] = skill_name
        if skill_name == "Angriff":
            skill_type = "att"
        elif skill_name == "Verteidigung":
            skill_type = "def"
        elif skill_name == "Geschicklichkeit":
            skill_type = "agi"
        else:
            continue
        skill_data["skill_type"] = skill_type
        level_td = table.find("td", string=re.compile("\\d+/"))
        if level_td:
            level_text = level_td.text.strip()
            level_match = re.search("(\\d+)/(.+)", level_text)
            if level_match:
                skill_data["current_level"] = int(level_match.group(1))
                max_level_str = level_match.group(2).strip()
                if "∞" in max_level_str:
                    skill_data["max_level"] = None
                else:
                    try:
                        skill_data["max_level"] = int(max_level_str)
                    except Exception:
                        skill_data["max_level"] = None
        cost_match = re.search("Nächste Stufe: €([\\d.,]+)", table.text)
        if cost_match:
            skill_data["next_level_cost"] = cost_match.group(1)
        duration_match = re.search("Dauer:\\s*([\\d:]+)", table.text)
        if duration_match:
            skill_data["duration"] = duration_match.group(1).strip()
        button = table.find("input", {"type": "button", "value": "Weiterbilden"})
        skill_data["can_start"] = button is not None
        available[skill_type] = skill_data
    skills["available_skills"] = available
    return skills


def parse_drinks(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    drinks = []
    forms = soup.find_all("form", action="/stock/foodstuffs/use/")
    for form in forms:
        drink = {}
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
            try:
                drink["effect"] = float(drink["promille"]) / 100.0
            except (ValueError, TypeError):
                drink["effect"] = 0.0
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
    soup = BeautifulSoup(html, "html.parser")
    food_items = []
    forms = soup.find_all("form", action="/stock/foodstuffs/use/")
    for form in forms:
        food = {}
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
            try:
                food["effect"] = float(food["promille"]) / 100.0
            except (ValueError, TypeError):
                food["effect"] = 0.0
        lager_input = form.find("input", {"id": f"lager_{food['name']}"})
        if lager_input:
            try:
                food["count"] = int(lager_input.get("value", "0"))
            except (ValueError, TypeError):
                food["count"] = 0
        else:
            food["count"] = 0
        if food.get("name") and food.get("item_id") and (food.get("effect", 0) < 0):
            food_items.append(food)
    return {"food": food_items}
