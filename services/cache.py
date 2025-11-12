"""
Caching layer for query results and embeddings
Reduces OpenAI API costs and improves response times
"""
import hashlib
import json
import time
from typing import List, Optional, Any, Dict
from datetime import datetime, timedelta
from collections import OrderedDict
import threading


class CacheEntry:
    """Single cache entry with TTL and metadata"""

    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0
        self.last_accessed = time.time()

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl_seconds == 0:  # 0 means no expiration
            return False
        return (time.time() - self.created_at) > self.ttl_seconds

    def access(self) -> Any:
        """Mark as accessed and return value"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value


class LRUCache:
    """
    Thread-safe LRU cache with TTL support
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize LRU cache

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds (0 = no expiration)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def _make_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None

            entry = self.cache[key]

            # Check if expired
            if entry.is_expired():
                del self.cache[key]
                self.misses += 1
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)

            self.hits += 1
            return entry.access()

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        with self.lock:
            ttl = ttl if ttl is not None else self.default_ttl

            # Remove oldest entries if at capacity
            while len(self.cache) >= self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.evictions += 1

            self.cache[key] = CacheEntry(value, ttl)
            self.cache.move_to_end(key)

    def delete(self, key: str):
        """Delete specific key"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]

    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0

    def cleanup_expired(self):
        """Remove all expired entries"""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self.cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests
            }


class EmbeddingsCache:
    """
    Specialized cache for OpenAI embeddings
    Saves costs by caching frequently embedded texts
    """

    def __init__(self, max_size: int = 10000, ttl: int = 86400):  # 24 hours default
        """
        Initialize embeddings cache

        Args:
            max_size: Maximum number of embeddings to cache
            ttl: Time to live in seconds (default 24 hours)
        """
        self.cache = LRUCache(max_size=max_size, default_ttl=ttl)

    def _text_to_key(self, text: str) -> str:
        """Generate cache key from text"""
        # Normalize text (lowercase, strip whitespace)
        normalized = text.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding for text"""
        key = self._text_to_key(text)
        return self.cache.get(key)

    def set_embedding(self, text: str, embedding: List[float]):
        """Cache embedding for text"""
        key = self._text_to_key(text)
        self.cache.set(key, embedding)

    def get_embeddings_batch(self, texts: List[str]) -> Dict[str, Optional[List[float]]]:
        """
        Get embeddings for multiple texts

        Returns:
            Dict mapping text to embedding (or None if not cached)
        """
        results = {}
        for text in texts:
            results[text] = self.get_embedding(text)
        return results

    def set_embeddings_batch(self, texts_and_embeddings: List[tuple]):
        """Cache multiple text-embedding pairs"""
        for text, embedding in texts_and_embeddings:
            self.set_embedding(text, embedding)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.cache.get_stats()
        stats["type"] = "embeddings"
        return stats


class QueryResultsCache:
    """
    Cache for query results to avoid repeated searches
    """

    def __init__(self, max_size: int = 500, ttl: int = 1800):  # 30 minutes default
        """
        Initialize query results cache

        Args:
            max_size: Maximum number of results to cache
            ttl: Time to live in seconds (default 30 minutes)
        """
        self.cache = LRUCache(max_size=max_size, default_ttl=ttl)

    def _query_to_key(self, query: str, filters: Optional[Dict] = None, top_k: int = 3) -> str:
        """Generate cache key from query parameters"""
        key_data = {
            "query": query.lower().strip(),
            "filters": filters or {},
            "top_k": top_k
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get_results(self, query: str, filters: Optional[Dict] = None, top_k: int = 3) -> Optional[Any]:
        """Get cached query results"""
        key = self._query_to_key(query, filters, top_k)
        return self.cache.get(key)

    def set_results(self, query: str, results: Any, filters: Optional[Dict] = None, top_k: int = 3):
        """Cache query results"""
        key = self._query_to_key(query, filters, top_k)
        self.cache.set(key, results)

    def invalidate_all(self):
        """Invalidate all cached results (e.g., after data update)"""
        self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.cache.get_stats()
        stats["type"] = "query_results"
        return stats


class CacheManager:
    """
    Centralized cache management for all cache types
    """

    def __init__(
        self,
        embeddings_cache_size: int = 10000,
        embeddings_ttl: int = 86400,
        query_cache_size: int = 500,
        query_ttl: int = 1800
    ):
        """Initialize cache manager with default caches"""
        self.embeddings_cache = EmbeddingsCache(
            max_size=embeddings_cache_size,
            ttl=embeddings_ttl
        )
        self.query_cache = QueryResultsCache(
            max_size=query_cache_size,
            ttl=query_ttl
        )

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all caches"""
        return {
            "embeddings": self.embeddings_cache.get_stats(),
            "query_results": self.query_cache.get_stats(),
        }

    def clear_all(self):
        """Clear all caches"""
        self.embeddings_cache.cache.clear()
        self.query_cache.cache.clear()

    def cleanup_all_expired(self):
        """Clean up expired entries in all caches"""
        self.embeddings_cache.cache.cleanup_expired()
        self.query_cache.cache.cleanup_expired()


# Global cache manager instance
cache_manager = CacheManager()


def calculate_cost_savings(stats: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate estimated cost savings from caching

    Args:
        stats: Cache statistics from get_all_stats()

    Returns:
        Dict with cost savings estimates
    """
    # OpenAI embedding costs (approximate)
    COST_PER_1K_TOKENS = 0.0001  # text-embedding-ada-002
    AVG_TOKENS_PER_TEXT = 100  # Conservative estimate

    embeddings_stats = stats.get("embeddings", {})
    hits = embeddings_stats.get("hits", 0)

    # Calculate saved API calls
    saved_tokens = hits * AVG_TOKENS_PER_TEXT
    saved_cost = (saved_tokens / 1000) * COST_PER_1K_TOKENS

    return {
        "saved_api_calls": hits,
        "estimated_saved_tokens": saved_tokens,
        "estimated_saved_cost_usd": round(saved_cost, 4),
        "hit_rate_percent": embeddings_stats.get("hit_rate_percent", 0)
    }
