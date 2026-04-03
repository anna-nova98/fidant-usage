# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prisma import Prisma
from typing import Optional
from datetime import date

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


db = Prisma()

@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()


@app.get("/usage")
async def get_usage():
    total = await db.request.count()
    requests = await db.request.find_many(order={"createdAt": "desc"}, take=10)
    return {"total_requests": total, "recent_requests": requests}

@app.get("/requests")
async def get_requests():
    return await db.request.find_many()

@app.post("/requests")
async def create_request(name: str, note: Optional[str] = None):
    return await db.request.create(data={
        "title": name,
        "content": note or "",
        "user_id": 0,
    })


@app.get("/stats")
async def get_stats():
    today = date.today()

 
    cache = await db.daily_usage_cache.find_unique(where={"date": today})
    
    if cache:
      
        return {"date": today, "total_usage": cache.total_usage, "cached": True}

    
    total_usage = await db.request.count() 

    await db.daily_usage_cache.create({
        "date": today,
        "total_usage": total_usage
    })

    return {"date": today, "total_usage": total_usage, "cached": False}