import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

_client: Optional[AsyncIOMotorClient] = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        _client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=15000,
        )
    return _client


def get_db():
    db_name = os.getenv("MONGODB_DATABASE", "sentinel")
    return get_client()[db_name]


async def insert_decision(doc: Dict[str, Any], snapshot: Optional[Dict] = None) -> str:
    db = get_db()
    decision_id = f"DEC-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    doc["decision_id"] = decision_id
    doc["logged_at"] = datetime.utcnow()
    if snapshot:
        doc["metrics_snapshot"] = snapshot
    await db.decisions.insert_one(doc)
    return decision_id


async def get_decisions(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    decision_type: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    db = get_db()
    query: Dict[str, Any] = {}
    if start or end:
        query["logged_at"] = {}
        if start:
            query["logged_at"]["$gte"] = start
        if end:
            query["logged_at"]["$lte"] = end
    if decision_type:
        query["decision_type"] = decision_type
    cursor = db.decisions.find(query).sort("logged_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_decision_by_id(decision_id: str) -> Optional[Dict]:
    db = get_db()
    return await db.decisions.find_one({"decision_id": decision_id})


async def get_decisions_in_lookback(
    outcome_date: datetime, lookback_min_days: int = 14, lookback_max_days: int = 90
) -> List[Dict]:
    start = outcome_date - timedelta(days=lookback_max_days)
    end = outcome_date - timedelta(days=lookback_min_days)
    return await get_decisions(start=start, end=end)


async def insert_warning(doc: Dict[str, Any]) -> str:
    db = get_db()
    warning_id = f"WARN-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    doc["warning_id"] = warning_id
    doc["fired_at"] = datetime.utcnow()
    await db.warnings.insert_one(doc)
    return warning_id


async def get_active_warnings(limit: int = 20) -> List[Dict]:
    db = get_db()
    cursor = db.warnings.find({"acknowledged": False}).sort("fired_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def acknowledge_warning(warning_id: str) -> bool:
    db = get_db()
    result = await db.warnings.update_one(
        {"warning_id": warning_id}, {"$set": {"acknowledged": True}}
    )
    return result.modified_count > 0
