"""
RuleShield Hermes -- 2-Layer Cache System

Layer 1: Exact hash match (SHA-256 of prompt text)
Layer 2: Semantic similarity via sentence-transformers embeddings
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import aiosqlite
import numpy as np

logger = logging.getLogger("ruleshield.cache")

# Rough per-token pricing used for cost estimation
INPUT_COST_PER_TOKEN = 0.005 / 1000   # $0.005 per 1k input tokens
OUTPUT_COST_PER_TOKEN = 0.015 / 1000  # $0.015 per 1k output tokens

# How many recent embeddings to compare against for semantic search
SEMANTIC_SEARCH_LIMIT = 200

_SCHEMA_CACHE = """
CREATE TABLE IF NOT EXISTS cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_hash TEXT UNIQUE NOT NULL,
    prompt_text TEXT NOT NULL,
    embedding BLOB,
    response TEXT NOT NULL,
    model TEXT,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_SCHEMA_SHADOW_LOG = """
CREATE TABLE IF NOT EXISTS shadow_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT NOT NULL,
    prompt_text TEXT,
    rule_response TEXT,
    llm_response TEXT,
    similarity REAL,
    length_ratio REAL,
    match_quality TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_SCHEMA_REQUEST_LOG = """
CREATE TABLE IF NOT EXISTS request_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_hash TEXT NOT NULL,
    prompt_text TEXT,
    response TEXT,
    model TEXT,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    resolution_type TEXT,
    latency_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def compute_prompt_hash(prompt_text: str) -> str:
    """SHA-256 hash of the prompt text."""
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


class CacheManager:
    """Two-layer async cache: exact hash lookup + semantic similarity fallback."""

    def __init__(
        self,
        db_path: str = "~/.ruleshield/cache.db",
        similarity_threshold: float = 0.92,
        cache_ttl_seconds: int = 3600,  # 1 hour default TTL
    ):
        self.db_path = str(Path(db_path).expanduser())
        self.similarity_threshold = similarity_threshold
        self.cache_ttl_seconds = cache_ttl_seconds
        self._db: aiosqlite.Connection | None = None
        self._embed_model: Any = None
        self._embed_available: bool | None = None  # None = not yet checked

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init(self) -> None:
        """Create the database directory, open the connection, and ensure tables exist."""
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)

        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(_SCHEMA_CACHE)
        await self._db.execute(_SCHEMA_SHADOW_LOG)
        await self._db.execute(_SCHEMA_REQUEST_LOG)
        await self._db.commit()
        logger.info("Cache database initialised at %s", self.db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None

    # ------------------------------------------------------------------
    # Embedding model (lazy load)
    # ------------------------------------------------------------------

    def _load_embed_model(self) -> bool:
        """Load the sentence-transformers model on first use.

        Returns True if the model is available, False otherwise.
        """
        if self._embed_available is not None:
            return self._embed_available

        try:
            from sentence_transformers import SentenceTransformer

            self._embed_model = SentenceTransformer("all-MiniLM-L6-v2")
            self._embed_available = True
            logger.info("Sentence-transformers model loaded for semantic caching")
        except Exception as exc:
            self._embed_available = False
            logger.warning(
                "sentence-transformers unavailable -- falling back to hash-only cache: %s",
                exc,
            )
        return self._embed_available

    def _encode(self, text: str) -> np.ndarray | None:
        """Return the embedding vector for *text*, or None if unavailable."""
        if not self._load_embed_model():
            return None
        return self._embed_model.encode(text, normalize_embeddings=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    # Keywords that indicate time-sensitive prompts (never cache these)
    _TEMPORAL_KEYWORDS: set[str] = {
        "now", "right now", "currently", "current", "today", "tonight",
        "this morning", "this afternoon", "this evening",
        "what time", "what's the time", "what date", "what day",
        "latest", "recent", "just happened", "breaking",
        "live", "real-time", "realtime", "at the moment",
        "how long ago", "minutes ago", "hours ago",
        "weather", "stock price", "exchange rate", "score",
        "jetzt", "gerade", "aktuell", "heute",  # German
    }

    def _is_temporal(self, prompt_text: str) -> bool:
        """Check if a prompt is time-sensitive and should not be cached."""
        lower = prompt_text.lower()
        return any(kw in lower for kw in self._TEMPORAL_KEYWORDS)

    async def check(self, prompt_hash: str, prompt_text: str) -> dict[str, Any] | None:
        """Check both cache layers.

        Returns a dict with keys ``response``, ``resolution_type``, and
        ``cache_type`` on a hit, or ``None`` on a miss.

        Time-sensitive prompts (containing "now", "today", "current", etc.)
        are never served from cache. Entries older than ``cache_ttl_seconds``
        are also skipped.
        """
        if self._db is None:
            await self.init()

        # Never cache time-sensitive queries
        if self._is_temporal(prompt_text):
            logger.debug("Skipping cache for temporal prompt: %s", prompt_text[:60])
            return None

        # --- Layer 1: exact hash ---
        row = await self._exact_lookup(prompt_hash)
        if row is not None:
            # TTL check: skip entries older than cache_ttl_seconds
            if self._is_expired(row):
                logger.debug("Cache entry expired (TTL): %s", prompt_hash[:16])
                return None
            await self._bump_hit_count(prompt_hash)
            return {
                "response": json.loads(row["response"]),
                "resolution_type": "cache",
                "cache_type": "exact",
            }

        # --- Layer 2: semantic similarity ---
        result = await self._semantic_lookup(prompt_text)
        if result is not None:
            if self._is_expired(result):
                logger.debug("Semantic cache entry expired (TTL): %s", result.get("prompt_hash", "?")[:16])
                return None
            await self._bump_hit_count(result["prompt_hash"])
            return {
                "response": json.loads(result["response"]),
                "resolution_type": "cache",
                "cache_type": "semantic",
            }

        return None

    def _is_expired(self, row: dict | Any) -> bool:
        """Check if a cache row has exceeded the TTL."""
        try:
            created = row["created_at"] if isinstance(row, dict) else row[8]  # created_at column
            if isinstance(created, str):
                from datetime import datetime, timezone
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                age_seconds = (datetime.now(timezone.utc) - created_dt).total_seconds()
            else:
                age_seconds = time.time() - float(created)
            return age_seconds > self.cache_ttl_seconds
        except Exception:
            return False  # if we can't determine age, assume valid

    async def store(
        self,
        prompt_hash: str,
        prompt_text: str,
        response: dict[str, Any],
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
    ) -> None:
        """Store a response in the cache table, including its embedding."""
        if self._db is None:
            await self.init()

        embedding_blob: bytes | None = None
        embedding = self._encode(prompt_text)
        if embedding is not None:
            embedding_blob = embedding.astype(np.float32).tobytes()

        response_json = json.dumps(response)

        try:
            await self._db.execute(
                """
                INSERT INTO cache
                    (prompt_hash, prompt_text, embedding, response, model,
                     tokens_in, tokens_out, cost_usd)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(prompt_hash) DO UPDATE SET
                    response   = excluded.response,
                    embedding  = excluded.embedding,
                    model      = excluded.model,
                    tokens_in  = excluded.tokens_in,
                    tokens_out = excluded.tokens_out,
                    cost_usd   = excluded.cost_usd
                """,
                (
                    prompt_hash,
                    prompt_text,
                    embedding_blob,
                    response_json,
                    model,
                    tokens_in,
                    tokens_out,
                    cost,
                ),
            )
            await self._db.commit()
        except Exception:
            logger.exception("Failed to store cache entry for hash %s", prompt_hash)

    async def log_request(
        self,
        prompt_hash: str,
        prompt_text: str,
        response: dict[str, Any],
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        resolution_type: str,
        latency_ms: int,
    ) -> None:
        """Append a row to the request_log table."""
        if self._db is None:
            await self.init()

        try:
            await self._db.execute(
                """
                INSERT INTO request_log
                    (prompt_hash, prompt_text, response, model,
                     tokens_in, tokens_out, cost_usd,
                     resolution_type, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prompt_hash,
                    prompt_text,
                    json.dumps(response),
                    model,
                    tokens_in,
                    tokens_out,
                    cost,
                    resolution_type,
                    latency_ms,
                ),
            )
            await self._db.commit()
        except Exception:
            logger.exception("Failed to log request for hash %s", prompt_hash)

    async def log_shadow(
        self,
        rule_id: str,
        prompt_text: str,
        rule_response: str,
        llm_response: str,
        similarity: float,
        length_ratio: float,
        match_quality: str,
    ) -> None:
        """Append a row to the shadow_log table for shadow mode comparison tracking."""
        if self._db is None:
            await self.init()

        try:
            await self._db.execute(
                """
                INSERT INTO shadow_log
                    (rule_id, prompt_text, rule_response, llm_response,
                     similarity, length_ratio, match_quality)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rule_id,
                    prompt_text,
                    rule_response,
                    llm_response,
                    similarity,
                    length_ratio,
                    match_quality,
                ),
            )
            await self._db.commit()
        except Exception:
            logger.exception("Failed to log shadow comparison for rule %s", rule_id)

    async def get_shadow_stats(
        self,
        limit: int | None = None,
        rule_id: str | None = None,
    ) -> dict[str, Any]:
        """Aggregate shadow mode comparison statistics."""
        if self._db is None:
            await self.init()

        stats: dict[str, Any] = {
            "total_comparisons": 0,
            "avg_similarity": 0.0,
            "per_rule": [],
            "ready_for_activation": [],
        }

        where_clauses: list[str] = []
        params: list[Any] = []
        if rule_id:
            where_clauses.append("rule_id = ?")
            params.append(rule_id)

        base_query = "SELECT * FROM shadow_log"
        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)
        if limit is not None:
            base_query = f"SELECT * FROM ({base_query} ORDER BY id DESC LIMIT ?) recent"
            params.append(limit)

        try:
            async with self._db.execute(
                f"SELECT COUNT(*) FROM ({base_query})",
                params,
            ) as cur:
                row = await cur.fetchone()
                stats["total_comparisons"] = row[0] if row else 0

            async with self._db.execute(
                f"SELECT AVG(similarity) FROM ({base_query})",
                params,
            ) as cur:
                row = await cur.fetchone()
                stats["avg_similarity"] = round(float(row[0] or 0), 4)

            async with self._db.execute(
                f"""
                SELECT
                    rule_id,
                    COUNT(*) AS total,
                    AVG(similarity) AS avg_sim,
                    SUM(CASE WHEN match_quality = 'good' THEN 1 ELSE 0 END) AS good,
                    SUM(CASE WHEN match_quality = 'partial' THEN 1 ELSE 0 END) AS partial,
                    SUM(CASE WHEN match_quality = 'poor' THEN 1 ELSE 0 END) AS poor
                FROM ({base_query})
                GROUP BY rule_id
                ORDER BY total DESC
                """,
                params,
            ) as cur:
                rows = await cur.fetchall()
                for r in rows:
                    entry = {
                        "rule_id": r[0],
                        "total": r[1],
                        "avg_similarity": round(float(r[2] or 0), 4),
                        "good": r[3],
                        "partial": r[4],
                        "poor": r[5],
                    }
                    stats["per_rule"].append(entry)
                    if entry["avg_similarity"] > 0.8:
                        stats["ready_for_activation"].append(entry["rule_id"])

        except Exception:
            logger.exception("Failed to compute shadow stats")

        return stats

    async def get_shadow_examples(
        self,
        limit: int = 5,
        match_quality: str | None = "poor",
        rule_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return concrete shadow comparison examples for rule tuning."""
        if self._db is None:
            await self.init()

        examples: list[dict[str, Any]] = []

        query = """
            SELECT
                rule_id,
                prompt_text,
                rule_response,
                llm_response,
                similarity,
                length_ratio,
                match_quality,
                created_at
            FROM shadow_log
        """
        params: list[Any] = []
        where_clauses: list[str] = []
        if match_quality:
            where_clauses.append("match_quality = ?")
            params.append(match_quality)
        if rule_id:
            where_clauses.append("rule_id = ?")
            params.append(rule_id)
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY similarity ASC, created_at DESC LIMIT ?"
        params.append(limit)

        try:
            async with self._db.execute(query, params) as cur:
                rows = await cur.fetchall()
                for row in rows:
                    examples.append({
                        "rule_id": row[0],
                        "prompt_text": row[1] or "",
                        "rule_response": row[2] or "",
                        "llm_response": row[3] or "",
                        "similarity": round(float(row[4] or 0.0), 4),
                        "similarity_pct": round(float(row[4] or 0.0) * 100, 1),
                        "length_ratio": round(float(row[5] or 0.0), 4),
                        "match_quality": row[6] or "unknown",
                        "created_at": row[7] or "",
                    })
        except Exception:
            logger.exception("Failed to fetch shadow examples")

        return examples

    async def reset_shadow_log(self, rule_id: str | None = None) -> int:
        """Delete shadow comparisons globally or for a single rule."""
        if self._db is None:
            await self.init()

        try:
            if rule_id:
                cur = await self._db.execute(
                    "DELETE FROM shadow_log WHERE rule_id = ?",
                    (rule_id,),
                )
            else:
                cur = await self._db.execute("DELETE FROM shadow_log")
            await self._db.commit()
            return int(cur.rowcount or 0)
        except Exception:
            logger.exception("Failed to reset shadow log")
            return 0

    async def get_stats(self) -> dict[str, Any]:
        """Aggregate cache and request-log statistics."""
        if self._db is None:
            await self.init()

        stats: dict[str, Any] = {
            "total_entries": 0,
            "total_requests": 0,
            "cache_hits": 0,
            "rule_hits": 0,
            "routed_calls": 0,
            "passthrough_calls": 0,
            "template_hits": 0,
            "llm_calls": 0,
            "total_savings": 0.0,
            "hit_rate": 0.0,
        }

        try:
            async with self._db.execute("SELECT COUNT(*) FROM cache") as cur:
                row = await cur.fetchone()
                stats["total_entries"] = row[0] if row else 0

            async with self._db.execute("SELECT COUNT(*) FROM request_log") as cur:
                row = await cur.fetchone()
                stats["total_requests"] = row[0] if row else 0

            async with self._db.execute(
                "SELECT COUNT(*) FROM request_log WHERE resolution_type = 'cache'"
            ) as cur:
                row = await cur.fetchone()
                stats["cache_hits"] = row[0] if row else 0

            async with self._db.execute(
                "SELECT COUNT(*) FROM request_log WHERE resolution_type = 'rule'"
            ) as cur:
                row = await cur.fetchone()
                stats["rule_hits"] = row[0] if row else 0

            async with self._db.execute(
                "SELECT COUNT(*) FROM request_log WHERE resolution_type = 'routed'"
            ) as cur:
                row = await cur.fetchone()
                stats["routed_calls"] = row[0] if row else 0

            async with self._db.execute(
                "SELECT COUNT(*) FROM request_log WHERE resolution_type = 'passthrough'"
            ) as cur:
                row = await cur.fetchone()
                stats["passthrough_calls"] = row[0] if row else 0

            async with self._db.execute(
                "SELECT COUNT(*) FROM request_log WHERE resolution_type = 'template'"
            ) as cur:
                row = await cur.fetchone()
                stats["template_hits"] = row[0] if row else 0

            async with self._db.execute(
                "SELECT COUNT(*) FROM request_log WHERE resolution_type = 'llm'"
            ) as cur:
                row = await cur.fetchone()
                stats["llm_calls"] = row[0] if row else 0

            # Savings = sum of cost for requests resolved without an LLM call
            async with self._db.execute(
                """
                SELECT COALESCE(SUM(cost_usd), 0)
                FROM request_log
                WHERE resolution_type IN ('cache', 'rule')
                """
            ) as cur:
                row = await cur.fetchone()
                stats["total_savings"] = round(float(row[0]), 6) if row else 0.0

            total = stats["total_requests"]
            hits = stats["cache_hits"] + stats["rule_hits"] + stats["template_hits"]
            stats["hit_rate"] = round(hits / total, 4) if total > 0 else 0.0

        except Exception:
            logger.exception("Failed to compute cache stats")

        return stats

    async def get_recent_requests(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return the most recent request-log entries."""
        if self._db is None:
            await self.init()

        results: list[dict[str, Any]] = []
        try:
            async with self._db.execute(
                "SELECT * FROM request_log ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ) as cur:
                rows = await cur.fetchall()
                for row in rows:
                    entry = dict(row)
                    # Deserialise the JSON response for the caller
                    if entry.get("response"):
                        try:
                            entry["response"] = json.loads(entry["response"])
                        except (json.JSONDecodeError, TypeError):
                            pass
                    results.append(entry)
        except Exception:
            logger.exception("Failed to fetch recent requests")

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _exact_lookup(self, prompt_hash: str) -> aiosqlite.Row | None:
        """Look up a cache entry by exact prompt hash."""
        async with self._db.execute(
            "SELECT * FROM cache WHERE prompt_hash = ?", (prompt_hash,)
        ) as cur:
            return await cur.fetchone()

    async def _semantic_lookup(self, prompt_text: str) -> dict[str, Any] | None:
        """Find the best semantic match among recent cached embeddings."""
        query_embedding = self._encode(prompt_text)
        if query_embedding is None:
            return None

        query_vec = query_embedding.astype(np.float32)

        try:
            async with self._db.execute(
                """
                SELECT prompt_hash, response, embedding
                FROM cache
                WHERE embedding IS NOT NULL
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (SEMANTIC_SEARCH_LIMIT,),
            ) as cur:
                rows = await cur.fetchall()
        except Exception:
            logger.exception("Semantic lookup query failed")
            return None

        best_score = -1.0
        best_row = None

        for row in rows:
            stored_vec = np.frombuffer(row["embedding"], dtype=np.float32)
            if stored_vec.shape != query_vec.shape:
                continue
            score = cosine_similarity(query_vec, stored_vec)
            if score > best_score:
                best_score = score
                best_row = row

        if best_row is not None and best_score >= self.similarity_threshold:
            logger.debug("Semantic cache hit (score=%.4f)", best_score)
            return {
                "prompt_hash": best_row["prompt_hash"],
                "response": best_row["response"],
                "score": best_score,
            }

        return None

    async def _bump_hit_count(self, prompt_hash: str) -> None:
        """Increment the hit_count for a cache entry."""
        try:
            await self._db.execute(
                "UPDATE cache SET hit_count = hit_count + 1 WHERE prompt_hash = ?",
                (prompt_hash,),
            )
            await self._db.commit()
        except Exception:
            logger.exception("Failed to bump hit count for %s", prompt_hash)
