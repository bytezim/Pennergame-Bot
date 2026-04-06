from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from .db import Base
from .constants import (
    VALID_TRAINING_SKILLS,
    DEFAULT_TRAINING_PAUSE,
    DEFAULT_TRAINING_MAX_LEVEL,
    BOTTLE_ENABLED_DEFAULT,
    TRAINING_ENABLED_DEFAULT,
    DEFAULT_BOTTLE_DURATION,
    DEFAULT_BOTTLE_PAUSE,
    AUTOSELL_ENABLED_DEFAULT,
    DEFAULT_AUTOSELL_MIN_PRICE,
    AUTODRINK_ENABLED_DEFAULT,
)


class Log(Base):
    __tablename__ = "logs"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    message = Column(String)


class IndexLogTimestamp(Index, Base):
    __tablename__ = 'idx_logs_timestamp'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
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
    __tablename__ = "bottle_prices"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    price_cents = Column(Integer, nullable=False)


class MoneyHistory(Base):
    __tablename__ = "money_history"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    amount = Column(Float, nullable=False)


class RankHistory(Base):
    __tablename__ = "rank_history"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    rank = Column(Integer, nullable=False)


class PointsHistory(Base):
    __tablename__ = "points_history"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    points = Column(Integer, nullable=False)


class BotActivity(Base):
    __tablename__ = "bot_activities"
    id = Column(Integer, primary_key=True)
    activity_type = Column(String, nullable=False)
    activity_subtype = Column(String, nullable=True)
    is_running = Column(Boolean, nullable=False, default=False)
    was_interrupted = Column(Boolean, default=False, nullable=False)
    start_time = Column(DateTime, nullable=True)
    expected_end_time = Column(DateTime, nullable=True)
    seconds_remaining = Column(Integer, nullable=True)
    additional_data = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ActivityQueue(Base):
    __tablename__ = "activity_queue"
    id = Column(Integer, primary_key=True)
    activity_type = Column(String, nullable=False)
    priority = Column(Integer, default=2)
    parallel = Column(Boolean, default=False)
    config = Column(String, nullable=True)
    status = Column(String, default="pending")
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class BotConfig(Base):
    __tablename__ = "bot_config"
    id = Column(Integer, primary_key=True)
    is_running = Column(Boolean, default=False, nullable=False)
    last_started = Column(DateTime, nullable=True)
    last_stopped = Column(DateTime, nullable=True)
    bottles_enabled = Column(Boolean, default=BOTTLE_ENABLED_DEFAULT, nullable=False)
    bottles_duration_minutes = Column(Integer, default=DEFAULT_BOTTLE_DURATION, nullable=False)
    bottles_pause_minutes = Column(Integer, default=DEFAULT_BOTTLE_PAUSE, nullable=False)
    bottles_autosell_enabled = Column(Boolean, default=AUTOSELL_ENABLED_DEFAULT, nullable=False)
    bottles_min_price = Column(Integer, default=DEFAULT_AUTOSELL_MIN_PRICE, nullable=False)
    training_enabled = Column(Boolean, default=TRAINING_ENABLED_DEFAULT, nullable=False)
    training_skills = Column(String, default='["att", "def", "agi"]', nullable=False)
    training_att_max_level = Column(Integer, default=DEFAULT_TRAINING_MAX_LEVEL, nullable=False)
    training_def_max_level = Column(Integer, default=DEFAULT_TRAINING_MAX_LEVEL, nullable=False)
    training_agi_max_level = Column(Integer, default=DEFAULT_TRAINING_MAX_LEVEL, nullable=False)
    training_pause_minutes = Column(Integer, default=DEFAULT_TRAINING_PAUSE, nullable=False)
    training_autodrink_enabled = Column(Boolean, default=AUTODRINK_ENABLED_DEFAULT, nullable=False)
    training_target_promille = Column(Float, default=3.5, nullable=False)
