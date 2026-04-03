from prisma import Prisma

# Single shared Prisma client instance for the application lifetime.
# Prisma's async interface is not thread-safe across multiple instances,
# so we use one global client connected on startup and disconnected on shutdown.
db = Prisma()


async def connect_db() -> None:
    """Open the database connection. Called once on application startup."""
    await db.connect()


async def disconnect_db() -> None:
    """Close the database connection. Called once on application shutdown."""
    await db.disconnect()


async def get_db() -> Prisma:
    """FastAPI dependency that provides the shared Prisma client."""
    return db
