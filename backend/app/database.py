from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from typing import Optional
from .config import settings

# Async MongoDB client for FastAPI
motor_client: Optional[AsyncIOMotorClient] = None

# Sync MongoDB client for initial setup/scripts
sync_client: Optional[MongoClient] = None


async def connect_to_mongo():
    """Connect to MongoDB asynchronously"""
    global motor_client
    motor_client = AsyncIOMotorClient(settings.MONGODB_URL)
    print(f"Connected to MongoDB at {settings.MONGODB_URL}")


async def close_mongo_connection():
    """Close MongoDB connection"""
    global motor_client
    if motor_client:
        motor_client.close()
        print("Closed MongoDB connection")


def get_database():
    """Get database instance"""
    if not motor_client:
        raise Exception("Database not connected. Call connect_to_mongo() first.")
    return motor_client[settings.DATABASE_NAME]


def get_sync_database():
    """Get synchronous database instance for scripts/initialization"""
    global sync_client
    if not sync_client:
        sync_client = MongoClient(settings.MONGODB_URL)
    return sync_client[settings.DATABASE_NAME]
