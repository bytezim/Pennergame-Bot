"""
Performance monitoring and metrics collection.

Tracks request times, cache hits, and other performance metrics.
"""

import time
from contextlib import contextmanager
from typing import Dict

from .logging_config import get_logger

logger = get_logger(__name__)


class PerformanceMonitor:
    """Simple performance monitoring for API endpoints."""

    def __init__(self):
        self.metrics: Dict[str, dict] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    @contextmanager
    def track_request(self, endpoint: str):
        """
        Context manager to track request duration.

        Usage:
            with perf_monitor.track_request("/api/status"):
                # ... do work ...
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self._record_request(endpoint, duration)

    def _record_request(self, endpoint: str, duration: float):
        """Record request metrics."""
        if endpoint not in self.metrics:
            self.metrics[endpoint] = {
                "count": 0,
                "total_time": 0.0,
                "min_time": float("inf"),
                "max_time": 0.0,
            }

        m = self.metrics[endpoint]
        m["count"] += 1
        m["total_time"] += duration
        m["min_time"] = min(m["min_time"], duration)
        m["max_time"] = max(m["max_time"], duration)

        # Log slow requests (>3s) - network requests to pennergame.de can be slow
        if duration > 5.0:
            logger.warning(f"Slow request: {endpoint} took {duration:.2f}s")

    def record_cache_hit(self):
        """Record cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self):
        """Record cache miss."""
        self.cache_misses += 1

    def get_stats(self) -> dict:
        """Get performance statistics."""
        stats = {}

        for endpoint, metrics in self.metrics.items():
            avg_time = (
                metrics["total_time"] / metrics["count"] if metrics["count"] > 0 else 0
            )

            stats[endpoint] = {
                "requests": metrics["count"],
                "avg_time": round(avg_time, 3),
                "min_time": round(metrics["min_time"], 3),
                "max_time": round(metrics["max_time"], 3),
            }

        # Cache statistics
        total_cache_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = (
            self.cache_hits / total_cache_requests if total_cache_requests > 0 else 0
        )

        stats["cache"] = {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "hit_rate": round(cache_hit_rate * 100, 2),
        }

        return stats

    def reset_stats(self):
        """Reset all statistics."""
        self.metrics = {}
        self.cache_hits = 0
        self.cache_misses = 0


# Global performance monitor instance
perf_monitor = PerformanceMonitor()
