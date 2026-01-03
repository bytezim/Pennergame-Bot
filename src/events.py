"""
Event-System für reaktive UI-Updates ohne excessive Polling
Reduziert Anfragen an pennergame.de durch intelligentes State-Tracking
"""

import json
import threading
from collections import defaultdict
from datetime import datetime
from queue import Queue
from typing import Any, Dict, List, Optional


class EventType:
    """Event-Typen für UI-Updates"""

    STATUS_CHANGED = "status_changed"
    ACTIVITY_STARTED = "activity_started"
    ACTIVITY_COMPLETED = "activity_completed"
    PENNER_DATA_UPDATED = "penner_data_updated"
    BOT_STATE_CHANGED = "bot_state_changed"
    LOG_ADDED = "log_added"
    BOTTLE_PRICE_CHANGED = "bottle_price_changed"
    MONEY_CHANGED = "money_changed"
    PROMILLE_CHANGED = "promille_changed"


class Event:
    """Einzelnes Event mit Daten"""

    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.type = event_type
        self.data = data
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_sse(self) -> str:
        """Formatiere als Server-Sent Event"""
        return f"data: {json.dumps(self.to_dict())}\n\n"


class EventBus:
    """
    Zentraler Event-Bus für das gesamte System
    Singleton-Pattern für globalen Zugriff
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._subscribers: Dict[str, List[Queue]] = defaultdict(list)
        self._all_subscribers: List[Queue] = []
        self._event_history: List[Event] = []
        self._max_history = 100
        self._lock = threading.Lock()
        self._initialized = True

    def subscribe(self, event_type: Optional[str] = None) -> Queue:
        """
        Abonniere Events

        Args:
            event_type: Spezifischer Event-Typ oder None für alle Events

        Returns:
            Queue die Events empfängt
        """
        queue = Queue(maxsize=100)

        with self._lock:
            if event_type:
                self._subscribers[event_type].append(queue)
            else:
                self._all_subscribers.append(queue)

        return queue

    def unsubscribe(self, queue: Queue, event_type: Optional[str] = None):
        """Entferne Queue von Subscriptions"""
        with self._lock:
            if event_type:
                if queue in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(queue)
            else:
                if queue in self._all_subscribers:
                    self._all_subscribers.remove(queue)

    def emit(self, event_type: str, data: Dict[str, Any]):
        """
        Sende Event an alle Subscriber

        Args:
            event_type: Typ des Events
            data: Event-Daten
        """
        event = Event(event_type, data)

        with self._lock:
            # Speichere in History
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)

            # Sende an spezifische Subscriber
            for queue in self._subscribers[event_type]:
                try:
                    queue.put_nowait(event)
                except:
                    pass  # Queue voll oder closed

            # Sende an "alle Events" Subscriber
            for queue in self._all_subscribers:
                try:
                    queue.put_nowait(event)
                except:
                    pass

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Hole letzte Events"""
        with self._lock:
            events = self._event_history[-limit:]
            return [e.to_dict() for e in events]

    def clear_history(self):
        """Lösche Event-History"""
        with self._lock:
            self._event_history.clear()


# Globale Instanz
event_bus = EventBus()


def emit_status_changed(activities: Dict[str, Any]):
    """Emit wenn sich Activity-Status ändert"""
    event_bus.emit(EventType.STATUS_CHANGED, {"activities": activities})


def emit_activity_started(activity_name: str, duration_seconds: int):
    """Emit wenn Activity gestartet wird"""
    event_bus.emit(
        EventType.ACTIVITY_STARTED,
        {"activity": activity_name, "duration_seconds": duration_seconds},
    )


def emit_activity_completed(activity_name: str):
    """Emit wenn Activity abgeschlossen ist"""
    event_bus.emit(EventType.ACTIVITY_COMPLETED, {"activity": activity_name})


def emit_penner_data_updated(penner_data: Dict[str, Any]):
    """Emit wenn Penner-Daten aktualisiert wurden"""
    event_bus.emit(EventType.PENNER_DATA_UPDATED, penner_data)


def emit_bot_state_changed(is_running: bool, config: Dict[str, Any]):
    """Emit wenn Bot gestartet/gestoppt wird"""
    event_bus.emit(
        EventType.BOT_STATE_CHANGED, {"is_running": is_running, "config": config}
    )


def emit_log_added(message: str):
    """Emit wenn neuer Log-Eintrag hinzugefügt wird"""
    event_bus.emit(
        EventType.LOG_ADDED,
        {"message": message, "timestamp": datetime.now().isoformat()},
    )


def emit_bottle_price_changed(price_cents: int):
    """Emit wenn sich Pfandflaschenpreis ändert"""
    event_bus.emit(EventType.BOTTLE_PRICE_CHANGED, {"price_cents": price_cents})


def emit_money_changed(amount: float):
    """Emit wenn sich Geldbetrag ändert"""
    formatted_money = (
        f"€{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    event_bus.emit(
        EventType.MONEY_CHANGED, {"money": formatted_money, "amount": amount}
    )


def emit_promille_changed(promille: float):
    """Emit wenn sich Promillewert ändert"""
    event_bus.emit(EventType.PROMILLE_CHANGED, {"promille": promille})
