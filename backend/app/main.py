import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.router import api_router
from app.bot.main import start_bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.makedirs("uploads/products", exist_ok=True)
os.makedirs("uploads/videos", exist_ok=True)

# Auto-migrate DB schema if new columns added
@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import text
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("ALTER TABLE products ADD COLUMN video_url VARCHAR;"))
            await session.commit()
            logger.info("Successfully added video_url column to products table.")
    except Exception as e:
        logger.info("Column video_url already exists or migration skipped.")

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("UPDATE product_images SET image_url = REPLACE(image_url, 'aishamebel-production.up.railway.app', 'aisha-mebel-production.up.railway.app');"))
            await session.commit()
            logger.info("Successfully updated product_images domain references.")
    except Exception as e:
        logger.info(f"Product image domain migration error/skipped: {e}")

    bot_task = asyncio.create_task(start_bot())
    yield
    bot_task.cancel()

app = FastAPI(
    title="AISHA MEBEL API",
    description="Production-ready digital commerce system",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "API is running."}

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
