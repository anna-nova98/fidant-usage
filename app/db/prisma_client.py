from prisma import Prisma


db = Prisma(adapter="sqlite")

async def connect_db():
    await db.connect()

async def disconnect_db():
    await db.disconnect()