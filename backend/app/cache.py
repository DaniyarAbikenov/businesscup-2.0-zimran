"""Redis usage (and why):
- sessions:   sess:<sha256(token)> -> user id, with TTL. Fast lookup on every request, logout = delete.
- throttle:   login:<email>|<ip> counter with 15 min TTL to slow password guessing.
- reminders:  followups:<user id> sorted set (member = case id, score = due unix time) powers the
              "follow-ups due" badge in the nav without hitting Postgres. Postgres stays the source of truth
              and the set is rebuilt from it at startup.
- LLM cache:  hint:<sha256(prompt facts)> so the optional AI draft is not paid for twice.
"""
import redis

from . import config

_client = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
    return _client
