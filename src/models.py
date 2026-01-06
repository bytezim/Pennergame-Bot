from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .db import Base


class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    message = Column(String)


class Cookie(Base):
    __tablename__ = "cookies"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)


class Penner(Base):
    __tablename__ = "penner"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    username = Column(String)
    location = Column(String)
    rank = Column(Integer)
    points = Column(Integer)
    money = Column(String)
    promille = Column(Float)
    att = Column(Integer)
    deff = Column(Integer)
    cleanliness = Column(Integer)
    status_message = Column(String)
    daily_task_done = Column(Boolean)
    container_capacity = Column(String)
    container_filled_percent = Column(Integer)
    container_donors = Column(Integer)
    container_total_donations = Column(String)
    container_donations_today = Column(Integer)
    container_ref_link = Column(String)
    weapon_name = Column(String)
    weapon_att = Column(Integer)
    home_name = Column(String)
    home_def = Column(Integer)
    instrument_name = Column(String)
    instrument_income_per_day = Column(String)
    instrument_payout = Column(String)
    schnorrplatz_name = Column(String)
    schnorrplatz_income_per_donation = Column(String)
    pet_name = Column(String)
    pet_attack = Column(Integer)
    pet_defense = Column(Integer)
    pet_tricks = Column(Integer)


class Plunder(Base):
    __tablename__ = "plunder"
    id = Column(Integer, primary_key=True)
    penner_id = Column(Integer, ForeignKey("penner.id"))
    slot = Column(String)
    name = Column(String)
    description = Column(String)
    rarity = Column(String)
    penner = relationship("Penner", back_populates="plunder")


Penner.plunder = relationship("Plunder", order_by=Plunder.id, back_populates="penner")


class Settings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=True)


class BottlePrice(Base):
    """Speichert die Historie der Pfandflaschenpreise (letzte 24h)"""

    __tablename__ = "bottle_prices"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    price_cents = Column(Integer, nullable=False)  # Preis in Cent (z.B. 21, 24, etc.)


class MoneyHistory(Base):
    """Speichert die Historie des Geldbetrags (letzte 24h)"""

    __tablename__ = "money_history"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    amount = Column(Float, nullable=False)  # Geldbetrag in Euro (z.B. 428200.98)


class RankHistory(Base):
    """Speichert die Historie des Rangs (letzte 24h)"""

    __tablename__ = "rank_history"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    rank = Column(Integer, nullable=False)  # Rang (z.B. 42, 100, etc.)


class PointsHistory(Base):
    """Speichert die Historie der Punkte (letzte 24h)"""

    __tablename__ = "points_history"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    points = Column(Integer, nullable=False)  # Punkte (z.B. 15000, 20000, etc.)


class BotConfig(Base):
    """Bot-Konfiguration für 24/7 Betrieb"""

    __tablename__ = "bot_config"
    id = Column(Integer, primary_key=True)

    # Bot Status
    is_running = Column(Boolean, default=False, nullable=False)
    last_started = Column(DateTime, nullable=True)
    last_stopped = Column(DateTime, nullable=True)

    # Pfandflaschen-Sammeln Konfiguration
    # Valid times: 10, 30, 60, 180, 360, 540, 720 minutes
    bottles_enabled = Column(Boolean, default=True, nullable=False)
    bottles_duration_minutes = Column(
        Integer, default=60, nullable=False
    )  # Sammeldauer in Minuten (nur vordefinierte Werte erlaubt)
    bottles_pause_minutes = Column(
        Integer, default=5, nullable=False
    )  # Pause zwischen Sammelaktionen

    # Pfandflaschen Auto-Verkauf Konfiguration
    bottles_autosell_enabled = Column(Boolean, default=False, nullable=False)
    bottles_min_price = Column(
        Integer, default=25, nullable=False
    )  # Mindestpreis in Cent (15-25)

    # Weiterbildungen Konfiguration
    training_enabled = Column(Boolean, default=False, nullable=False)
    training_skills = Column(
        String, default='["att", "def", "agi"]', nullable=False
    )  # JSON-Array der aktiven Skills (z.B. ["att", "def"])
    training_att_max_level = Column(
        Integer, default=999, nullable=False
    )  # Max Level für Angriff (999 = kein Limit)
    training_def_max_level = Column(
        Integer, default=999, nullable=False
    )  # Max Level für Verteidigung (999 = kein Limit)
    training_agi_max_level = Column(
        Integer, default=999, nullable=False
    )  # Max Level für Geschicklichkeit (999 = kein Limit)
    training_pause_minutes = Column(
        Integer, default=5, nullable=False
    )  # Pause zwischen Weiterbildungen

    # Weiterbildungen Auto-Trinken Konfiguration
    training_autodrink_enabled = Column(
        Boolean, default=False, nullable=False
    )  # Automatisch vor Training trinken
    training_target_promille = Column(
        Float, default=2.5, nullable=False
    )  # Ziel-Promillewert (2.0-3.0)
