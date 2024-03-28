import json
from typing import Set, Dict, List
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Float,
    DateTime,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
from datetime import datetime
from pydantic import BaseModel, field_validator
from config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
)

# FastAPI app setup
app = FastAPI()
# SQLAlchemy setup
DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(DATABASE_URL)
metadata = MetaData()
# Define the ProcessedAgentData table
processed_agent_data = Table(
    "processed_agent_data",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("road_state", String),
    Column("x", Float),
    Column("y", Float),
    Column("z", Float),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("timestamp", DateTime),
)
SessionLocal = sessionmaker(bind=engine)


# FastAPI models
class AccelerometerData(BaseModel):
    x: float
    y: float
    z: float


class GpsData(BaseModel):
    latitude: float
    longitude: float


class AgentData(BaseModel):
    accelerometer: AccelerometerData
    gps: GpsData
    timestamp: datetime
    
    @classmethod
    @field_validator('timestamp', mode='before')
    def check_timestamp(cls, value):
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            raise ValueError("Invalid timestamp format. Expected ISO 8601 format(YYYY-MM-DDTHH:MM:SSZ).")


class ProcessedAgentData(BaseModel):
    road_state: str
    agent_data: AgentData
    
# WebSocket subscriptions
subscriptions: Dict[int, Set[WebSocket]] = {}

# Database model
class ProcessedAgentDataInDB(BaseModel):
    id: int
    road_state: str
    x: float
    y: float
    z: float
    latitude: float
    longitude: float
    timestamp: datetime


# FastAPI app setup
app = FastAPI()

# WebSocket subscriptions
subscriptions: Set[WebSocket] = set()

# FastAPI WebSocket endpoint
@app.websocket("/ws/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    subscriptions.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        subscriptions.remove(websocket)
        
        
# Function to send data to subscribed users
async def send_data_to_subscribers(data):
    for websocket in subscriptions:
        await websocket.send_json(json.dumps(data))


@app.post("/processed_agent_data/")
async def create_processed_agent_data(data: List[ProcessedAgentData]):
    with SessionLocal() as session:
        for el in data:
            item = ProcessedAgentDataInDB(
                road_state=el.road_state,
                x=el.x,
                y=el.y,
                z=el.z,
                latitude=el.latitude,
                longitude=el.longitude,
                timestamp=el.datetime
            )
            
            session.add(item)
        session.commit()

    await send_data_to_subscribers(data)
    return {"message": "Data added successfully"}
    
    
@app.get(
    "/processed_agent_data/{processed_agent_data_id}",
    response_model=ProcessedAgentDataInDB
)
def read_processed_agent_data(processed_agent_data_id: int):
    with SessionLocal() as session:
        query = select(ProcessedAgentDataInDB).filter(ProcessedAgentDataInDB.id == processed_agent_data_id)
        data = session.execute(query)
        if not data:
            raise HTTPException(status_code=404, detail="Data not found")
        
        return data


@app.get(
    "/processed_agent_data/",
    response_model=list[ProcessedAgentDataInDB]
)
def list_processed_agent_data():
    with SessionLocal() as session:
        query = select(ProcessedAgentDataInDB)
        list = session.execute(query).all()
        return list


@app.put(
    "/processed_agent_data/{processed_agent_data_id}",
    response_model=ProcessedAgentDataInDB
)
def update_processed_agent_data(processed_agent_data_id: int, data: ProcessedAgentData):
    with SessionLocal() as session:
        item = session.query(ProcessedAgentDataInDB).filter(ProcessedAgentDataInDB.id == processed_agent_data_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Data not found")

        item.road_state = data.road_state
        item.x = data.x
        item.y = data.y
        item.z = data.z
        item.latitude = data.latitude
        item.longitude = data.longitude
        item.timestamp = data.datetime

        session.commit()
        session.refresh(item)
        return item
    
    
@app.delete(
    "/processed_agent_data/{processed_agent_data_id}",
    response_model=ProcessedAgentDataInDB
)
def delete_processed_agent_data(processed_agent_data_id: int):
    with SessionLocal() as session:
        item = session.query(ProcessedAgentDataInDB).filter(ProcessedAgentDataInDB.id == processed_agent_data_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Data not found")

        session.delete(item)
        session.commit()
        return item 


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="127.0.0.1", port=8000)