import functools
import hashlib
import json
import time
from typing import Any, Callable, Dict, Optional
from .logging_config import get_logger

logger = get_logger(__name__)


def _get_perf_monitor():
    try:
        from .performance import perf_monitor

        return perf_monitor
    except ImportError:
        return None


class CacheEntry:
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expires_at = time.time() + ttl

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class Cache:
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[Any]:
        perf = _get_perf_monitor()
        if key not in self._cache:
            self._misses += 1
            if perf:
                perf.record_cache_miss()
            return None
        entry = self._cache[key]
        if entry.is_expired():
            logger.debug(f"Cache expired: {key}")
            del self._cache[key]
            self._misses += 1
            if perf:
                perf.record_cache_miss()
            return None
        self._hits += 1
        if perf:
            perf.record_cache_hit()
        return entry.value

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if len(self._cache) >= self._max_size:
            self._evict_oldest()
        self._cache[key] = CacheEntry(value, ttl)
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache deleted: {key}")

    def invalidate_pattern(self, pattern: str) -> int:
        keys_to_delete = [k for k in self._cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self._cache[key]
        if keys_to_delete:
            logger.info(
                f"Invalidated {len(keys_to_delete)} cache entries matching: {pattern}"
            )
        return len(keys_to_delete)

    def clear(self) -> None:
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared: {count} entries removed")

    def _evict_oldest(self) -> None:
        if self._cache:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._evictions += 1
            logger.debug(f"Cache eviction: {oldest_key}")

    def get_stats(self) -> Dict[str, Any]:
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests * 100 if total_requests > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": round(hit_rate, 2),
        }


app_cache = Cache(max_size=1000)


def cached(ttl: int = 300, key_prefix: str = ""):

    def decorator(func: Callable) -> Callable:

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key_parts = [key_prefix, func.__name__]
            if args or kwargs:
                args_str = json.dumps(
                    {"args": args, "kwargs": kwargs}, sort_keys=True, default=str
                )
                args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
                key_parts.append(args_hash)
            cache_key = ":".join(filter(None, key_parts))
            cached_value = app_cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            app_cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


def invalidate_cache_pattern(pattern: str) -> int:
    return app_cache.invalidate_pattern(pattern)


def get_cache_stats() -> Dict[str, Any]:
    return app_cache.get_stats()
