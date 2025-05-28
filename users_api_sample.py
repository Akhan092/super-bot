from fastapi import FastAPI
from database import database, users

app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/users19034006343")
async def get_users():
    query = users.select()
    result = await database.fetch_all(query)
    return result