# Cache: Add Redis backend option

**Labels:** `good first issue`, `help wanted`, `cache`, `enhancement`, `infrastructure`

## Description

Add an optional Redis backend for RuleShield's cache layer. Currently, the cache uses SQLite exclusively (`~/.ruleshield/cache.db`), which works well for single-instance deployments but does not support distributed setups where multiple proxy instances need to share a cache. A Redis backend would enable RuleShield to run across multiple instances behind a load balancer, sharing cached responses.

## Why this is useful

Teams running RuleShield in production often need multiple proxy instances for high availability and throughput. With SQLite, each instance maintains its own cache, so a cache hit on instance A does not help instance B. Redis is the standard solution for shared, fast, in-memory caching across distributed services. Adding Redis support makes RuleShield production-ready for teams at scale.

## Where to look in the codebase

### Current cache implementation

**File:** `ruleshield/cache.py`

The `CacheManager` class (line ~92) handles all cache operations:

- `__init__()` -- Sets up the SQLite database path and config
- `init()` -- Opens the SQLite connection and creates tables
- `check()` -- Two-layer lookup: exact hash (Layer 1) + semantic similarity (Layer 2)
- `store()` -- Saves a response with its embedding to the cache table
- `log_request()` -- Appends to `request_log` (this should remain SQLite-only for durability)
- `_exact_lookup()` -- Queries by prompt hash
- `_semantic_lookup()` -- Compares embeddings for semantic similarity

### Configuration

**File:** `ruleshield/config.py`

The `Settings` dataclass (line ~31) needs two new fields:

```python
cache_backend: str = "sqlite"  # "sqlite" or "redis"
redis_url: str = ""            # e.g., "redis://localhost:6379/0"
```

And `_env_overrides()` (line ~74) needs corresponding environment variable support:

```python
if val := os.getenv("RULESHIELD_CACHE_BACKEND"):
    settings.cache_backend = val
if val := os.getenv("RULESHIELD_REDIS_URL"):
    settings.redis_url = val
```

### Proxy startup

**File:** `ruleshield/proxy.py`

The proxy creates the `CacheManager` during startup in the `lifespan()` function. This is where you would check `settings.cache_backend` and instantiate either the SQLite or Redis cache manager.

## Implementation approach

### Option A: Adapter pattern (recommended)

Create an abstract base class or protocol for the cache interface, then implement both SQLite and Redis backends:

```python
# ruleshield/cache.py (or a new file: ruleshield/cache_redis.py)

class RedisCacheManager:
    """Redis-backed cache for distributed deployments."""

    def __init__(self, redis_url: str, similarity_threshold: float = 0.92):
        self.redis_url = redis_url
        self.similarity_threshold = similarity_threshold
        self._redis = None

    async def init(self) -> None:
        import redis.asyncio as aioredis
        self._redis = aioredis.from_url(self.redis_url)

    async def check(self, prompt_hash: str, prompt_text: str) -> dict | None:
        # Layer 1: exact hash lookup using Redis GET
        cached = await self._redis.get(f"ruleshield:cache:{prompt_hash}")
        if cached:
            return json.loads(cached)
        # Layer 2: semantic search is more complex with Redis
        # (can use Redis Vector Search or skip for v1)
        return None

    async def store(self, prompt_hash, prompt_text, response, model, tokens_in, tokens_out, cost):
        await self._redis.set(
            f"ruleshield:cache:{prompt_hash}",
            json.dumps({"response": response, "model": model}),
            ex=self.cache_ttl_seconds,
        )
```

### Option B: Redis for Layer 1 only

A simpler approach: use Redis only for the exact-hash cache layer, and keep the semantic similarity layer and request_log in SQLite. This gives the distributed cache benefit without the complexity of vector search in Redis.

## Acceptance criteria

- [ ] `Settings` in `ruleshield/config.py` has `cache_backend` and `redis_url` fields
- [ ] Environment variables `RULESHIELD_CACHE_BACKEND` and `RULESHIELD_REDIS_URL` are supported
- [ ] A `RedisCacheManager` class exists (either in `ruleshield/cache.py` or a new `ruleshield/cache_redis.py`)
- [ ] `RedisCacheManager` implements at least `init()`, `check()`, `store()`, and `close()` methods
- [ ] The exact-hash cache layer (Layer 1) works with Redis
- [ ] The proxy startup in `ruleshield/proxy.py` selects the correct cache backend based on config
- [ ] `request_log` functionality continues to use SQLite (Redis is for cache only)
- [ ] When `cache_backend` is `"sqlite"` (default), behavior is unchanged
- [ ] `redis` is added as an optional dependency in `pyproject.toml` (e.g., under `[project.optional-dependencies]`)
- [ ] A helpful error message is shown if `cache_backend` is `"redis"` but the `redis` package is not installed
- [ ] Existing tests still pass

## Estimated difficulty

**Medium** -- Requires understanding the cache interface, async Python, and basic Redis operations. The code changes are well-scoped but span multiple files.

## Helpful links and references

- [Cache source](../../ruleshield/cache.py) -- Current SQLite implementation
- [Config source](../../ruleshield/config.py) -- Settings and environment variable handling
- [Proxy source](../../ruleshield/proxy.py) -- Where cache is initialized at startup
- [pyproject.toml](../../pyproject.toml) -- Dependency management
- redis-py async docs: https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html
- Redis commands reference: https://redis.io/commands/
