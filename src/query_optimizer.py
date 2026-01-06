"""
Query optimization utilities to prevent N+1 queries.

Provides helpers for eager loading and batch operations.
"""

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from .logging_config import get_logger
from .models import Log, MoneyHistory, PointsHistory, RankHistory

logger = get_logger(__name__)


def get_recent_logs_batch(session: Session, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get recent logs efficiently (single query).

    Args:
        session: Database session
        limit: Maximum number of logs

    Returns:
        List of log dictionaries
    """
    logs = session.query(Log).order_by(Log.id.desc()).limit(limit).all()

    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "message": log.message,
        }
        for log in logs
    ]


def batch_delete_old_records(session: Session, hours: int = 24) -> Dict[str, int]:
    """
    Delete old records in batch (single query per table).

    Args:
        session: Database session
        hours: Delete records older than this

    Returns:
        Dictionary with deleted counts per table
    """
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(hours=hours)

    # Batch deletes (much faster than individual deletes)
    logs_deleted = session.query(Log).filter(Log.timestamp < cutoff).delete()
    money_deleted = (
        session.query(MoneyHistory).filter(MoneyHistory.timestamp < cutoff).delete()
    )
    rank_deleted = (
        session.query(RankHistory).filter(RankHistory.timestamp < cutoff).delete()
    )
    points_deleted = (
        session.query(PointsHistory).filter(PointsHistory.timestamp < cutoff).delete()
    )

    session.commit()

    deleted = {
        "logs": logs_deleted,
        "money_history": money_deleted,
        "rank_history": rank_deleted,
        "points_history": points_deleted,
        "total": logs_deleted + money_deleted + rank_deleted + points_deleted,
    }

    if deleted["total"] > 0:
        logger.info(f"Batch deleted {deleted['total']} old records")

    return deleted
