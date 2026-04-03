from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date, datetime, timedelta, timezone
from typing import TypedDict
from prisma import Prisma
from app.db.prisma_client import get_db
from app.utils.auth import get_current_user_id

router = APIRouter(prefix="/api/usage", tags=["usage"])

# Daily turn limits per subscription tier.
# "starter" is also used as the fallback for any unrecognised plan.
PLAN_LIMITS: dict[str, int] = {"starter": 30, "pro": 100, "executive": 500}

# A cached aggregate older than this is considered stale and will be recomputed.
CACHE_STALE_MINUTES: int = 5

# Reservations older than this are considered expired and excluded from the
# "reserved" counter, matching the reserve → commit lifecycle timeout.
RESERVATION_TTL_MINUTES: int = 15


class DayCounts(TypedDict):
    committed: int
    reserved: int


def _date_range(from_date: date, to_date: date) -> list[date]:
    """Return an inclusive list of dates from from_date to to_date."""
    days = (to_date - from_date).days + 1
    return [from_date + timedelta(days=i) for i in range(days)]


def _as_utc(dt: datetime) -> datetime:
    """
    Ensure a datetime is timezone-aware (UTC).

    SQLite stores datetimes as naive UTC strings. Prisma returns them as
    naive datetime objects, so we attach UTC explicitly when tzinfo is absent.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def _compute_day(db: Prisma, user_id: int, day: date) -> DayCounts:
    """
    Query raw events for a single day and return committed/reserved counts.

    - committed: events with status == "committed" (all of them count)
    - reserved:  events with status == "reserved" that are NOT yet expired
                 (reserved_at within the last RESERVATION_TTL_MINUTES)
    """
    date_key = day.isoformat()
    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=RESERVATION_TTL_MINUTES)

    events = await db.daily_usage_events.find_many(
        where={"user_id": user_id, "date_key": date_key}
    )

    committed = sum(1 for e in events if e.status == "committed")
    reserved = sum(
        1 for e in events
        if e.status == "reserved" and _as_utc(e.reserved_at) >= stale_cutoff
    )

    return DayCounts(committed=committed, reserved=reserved)


async def _get_day_cached(db: Prisma, user_id: int, day: date) -> DayCounts:
    """
    Return daily counts, using the cache when available and fresh.

    Cache strategy:
    - Today is always computed live (data is still changing throughout the day).
    - Past days are read from daily_usage_cache if the entry exists and was
      computed within the last CACHE_STALE_MINUTES.
    - On a cache miss or stale hit, raw events are queried and the cache is
      upserted so subsequent requests are fast.
    """
    date_key = day.isoformat()
    cache_stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=CACHE_STALE_MINUTES)
    is_past_day = day < date.today()

    if is_past_day:
        cache = await db.daily_usage_cache.find_unique(
            where={"user_id_date_key": {"user_id": user_id, "date_key": date_key}}
        )
        if cache and _as_utc(cache.computed_at) >= cache_stale_cutoff:
            # Cache hit — return precomputed aggregates
            return DayCounts(committed=cache.committed_count, reserved=cache.reserved_count)

    # Cache miss, stale, or today — fall back to raw query
    counts = await _compute_day(db, user_id, day)

    # Persist the result for past days so future requests skip the raw scan
    if is_past_day:
        await db.daily_usage_cache.upsert(
            where={"user_id_date_key": {"user_id": user_id, "date_key": date_key}},
            data={
                "create": {
                    "user_id": user_id,
                    "date_key": date_key,
                    "committed_count": counts["committed"],
                    "reserved_count": counts["reserved"],
                },
                "update": {
                    "committed_count": counts["committed"],
                    "reserved_count": counts["reserved"],
                    "computed_at": datetime.now(timezone.utc),
                },
            },
        )

    return counts


@router.get("/stats")
async def get_usage_stats(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to include (1–90)"),
    user_id: int = Depends(get_current_user_id),
    db: Prisma = Depends(get_db),
):
    """
    GET /api/usage/stats?days=7

    Returns usage analytics for the authenticated user over the requested period.

    The response includes:
    - Per-day breakdown of committed turns, active reservations, and utilization
    - A summary with totals, daily average, peak day, and current active streak

    Utilization is expressed as a ratio (0.0–1.0) of committed turns vs. daily limit.
    Days with no events are included with zero values to ensure a complete date range.
    """
    user = await db.users.find_unique(where={"id": user_id})
    if not user:
        # The token was structurally valid but references a non-existent user
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "User not found"},
        )

    daily_limit = PLAN_LIMITS.get(user.plan_tier, PLAN_LIMITS["starter"])
    to_date = date.today()
    from_date = to_date - timedelta(days=days - 1)

    # Build per-day stats, fetching from cache where possible
    day_results = []
    for day in _date_range(from_date, to_date):
        counts = await _get_day_cached(db, user_id, day)
        utilization = round(counts["committed"] / daily_limit, 4) if daily_limit else 0.0
        day_results.append({
            "date": day.isoformat(),
            "committed": counts["committed"],
            "reserved": counts["reserved"],
            "limit": daily_limit,
            "utilization": utilization,
        })

    total_committed = sum(d["committed"] for d in day_results)
    # Average over the full requested period (including zero days) to reflect
    # actual usage density rather than only active days
    avg_daily = round(total_committed / days, 1)

    peak = max(day_results, key=lambda d: d["committed"])
    peak_day = {"date": peak["date"], "count": peak["committed"]}

    # Streak: count consecutive days ending today where committed > 0
    streak = 0
    for d in reversed(day_results):
        if d["committed"] > 0:
            streak += 1
        else:
            break

    return {
        "plan": user.plan_tier,
        "daily_limit": daily_limit,
        "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "days": day_results,
        "summary": {
            "total_committed": total_committed,
            "avg_daily": avg_daily,
            "peak_day": peak_day,
            "current_streak": streak,
        },
    }
