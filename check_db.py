import asyncio
from prisma import Prisma

async def main():
    db = Prisma(adapter='sqlite', url='file:./prisma/dev.db')
    await db.connect()

    # 이미 존재하면 삭제 후 삽입
    await db.request.delete_many()

    # 더미 데이터 삽입
    await db.request.create(
        data={
            "title": "첫 번째 요청",
            "content": "내용입니다.",
            "user_id": 1
        }
    )
    await db.request.create(
        data={
            "title": "두 번째 요청",
            "content": "두 번째 내용입니다.",
            "user_id": 2
        }
    )

    print("더미 데이터 삽입 완료")
    await db.disconnect()

asyncio.run(main())