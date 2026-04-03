"""
Seed script — populates the database with a test user and sample usage events.

Run with:
    python prisma/seed.py

Creates:
- 1 user (id=1, starter plan) matching the demo AUTH_TOKEN="1" in the frontend
- 14 days of realistic daily_usage_events so the dashboard has data to display
"""

import asyncio
import random
from datetime import date, datetime, timedelta, timezone
from prisma import Prisma


SEED_USER = {
    "email": "demo@fidant.ai",
    "name": "Demo User",
    "plan_tier": "starter",  # daily limit: 30
}

SEED_DAYS = 14  # number of past days to populate


async def main() -> None:
    db = Prisma()
    await db.connect()

    # Upsert so re-running the seed is safe
    user = await db.users.upsert(
        where={"email": SEED_USER["email"]},
        data={"create": SEED_USER, "update": {}},
    )
    print(f"User ready: id={user.id} email={user.email} plan={user.plan_tier}")

    today = date.today()
    total_events = 0

    for i in range(SEED_DAYS, 0, -1):
        day = today - timedelta(days=i)
        date_key = day.isoformat()

        # Randomise committed turns per day (0-30), weighted toward moderate usage
        committed_count = random.choices(
            [0, random.randint(1, 10), random.randint(10, 25), random.randint(25, 30)],
            weights=[10, 50, 30, 10],
        )[0]

        for j in range(committed_count):
            ts = datetime(
                day.year, day.month, day.day,
                random.randint(8, 22), random.randint(0, 59),
                tzinfo=timezone.utc,
            )
            await db.daily_usage_events.create(data={
                "user_id": user.id,
                "date_key": date_key,
                "request_id": f"req_{date_key}_{j:03d}",
                "status": "committed",
                "reserved_at": ts,
                "committed_at": ts,
            })
            total_events += 1

        print(f"  {date_key}: {committed_count} events")

    print(f"\nDone. Seeded {total_events} events across {SEED_DAYS} days.")
    await db.disconnect()


asyncio.run(main())
