from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from database import database, users, metadata
import sqlalchemy
import random
import requests

app = FastAPI()
engine = sqlalchemy.create_engine(str(database.url))
metadata.create_all(engine)
templates = Jinja2Templates(directory="templates")

# 🔐 smsc.kz параметрлері
SMS_LOGIN = "Ahan1992"
SMS_PASSWORD = "Ahan5250!"

# 🔄 Уақытша сессия кодтары (продакшн үшін Redis қолдану ұсынылады)
sms_codes = {}

# 📦 Телефон нөмірін тазалау функциясы
def clean_phone(phone: str) -> str:
    return phone.replace("+", "").replace("(", "").replace(")", "").replace(" ", "").replace("-", "")

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

@app.post("/send_code")
async def send_code(phone: str = Form(...)):
    cleaned = clean_phone(phone)
    code = str(random.randint(100000, 999999))
    sms_codes[cleaned] = code

    print(f"[SMS] Код {code} жіберілді: {cleaned}")  # ✅ Debug үшін

    url = f"https://smsc.kz/sys/send.php?login={SMS_LOGIN}&psw={SMS_PASSWORD}&phones={cleaned}&mes=Код:%20{code}&fmt=3"
    response = requests.get(url)

    if response.status_code == 200:
        return JSONResponse({"ok": True, "msg": "Код жіберілді ✅"})
    else:
        return JSONResponse({"ok": False, "msg": "Қате: код жіберілмеді ❌"}, status_code=500)

@app.post("/register_user")
async def register_user(
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    sms_code: str = Form(...)
):
    cleaned = clean_phone(phone)
    expected_code = sms_codes.get(cleaned)

    print(f"[DEBUG] Күтілген код: {expected_code}, енгізілген код: {sms_code}, cleaned: {cleaned}")  # ✅ Debug

    if not expected_code or sms_code != expected_code:
        return JSONResponse({"ok": False, "msg": "❌ Код дұрыс емес"}, status_code=400)

    query = users.insert().values(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        password=password
    )
    await database.execute(query)
    return JSONResponse({"ok": True, "msg": "✅ Пайдаланушы тіркелді!"})
