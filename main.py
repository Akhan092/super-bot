from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import database, users, metadata
import sqlalchemy

app = FastAPI()
engine = sqlalchemy.create_engine(str(database.url))
metadata.create_all(engine)
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register_user")
async def register_user(
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...)
):
    query = users.insert().values(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        password=password
    )
    await database.execute(query)
    return {"message": "Пайдаланушы базаға сақталды ✅"}

@app.get("/users19034006343")
async def get_users():
    query = users.select()
    result = await database.fetch_all(query)
    return result
