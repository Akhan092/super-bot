# ✅ Құпиясөзді қалпына келтіруге толық қолдау қосылған FastAPI сервер

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from database import database, users, metadata
import sqlalchemy
import random
import requests
from datetime import datetime
from sqlalchemy import text

app = FastAPI()

# PostgreSQL Engine
engine = sqlalchemy.create_engine(str(database.url))
metadata.create_all(engine)
templates = Jinja2Templates(directory="templates")

# Textbelt API
SMS_API_KEY = "58ed0414c9e959d68d66c2b55e0a4c576e2a4c52BgRzbptGWysU5P2wvItnvUbHD"

# Кодтарды уақытша сақтау
sms_codes = {}

# Телефон форматтау
def clean_phone(phone: str) -> str:
    return phone.replace("+7", "7").replace("(", "").replace(")", "").replace(" ", "").replace("-", "")

# Базаға қосылу
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Басты бет
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Тіркелу беті
@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Құпиясөзді ұмыттым беті
@app.get("/forgot_password", response_class=HTMLResponse)
async def forgot_password(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

# ✅ СМС код жіберу (барлық режимдер үшін)
@app.post("/send_code")
async def send_code(phone: str = Form(...)):
    cleaned = clean_phone(phone)

    # ✅ Код генерациялау және сақтау
    code = str(random.randint(100000, 999999))
    sms_codes[cleaned] = code
    print(f"[SMS] Код {code} жіберілді: {cleaned}")

    # Textbelt арқылы СМС жіберу
    payload = {
        "phone": cleaned,
        "message": f"Кіру коды: {code}",
        "key": SMS_API_KEY
    }

    response = requests.post("https://textbelt.com/text", data=payload)

    try:
        data = response.json()
    except Exception as e:
        return JSONResponse({"ok": False, "msg": f"JSON қатесі: {str(e)}", "raw": response.text}, status_code=500)

    if data.get("success"):
        return JSONResponse({"ok": True, "msg": "Код жіберілді ✅"})
    else:
        return JSONResponse({"ok": False, "msg": "Қате: код жіберілмеді ❌", "data": data}, status_code=500)

# ✅ СМС кодты тексеру
@app.post("/verify_code")
async def verify_code(phone: str = Form(...), code: str = Form(...)):
    cleaned = clean_phone(phone)
    expected_code = sms_codes.get(cleaned)

    print(f"[VERIFY] Күтілген код: {expected_code}, келген код: {code}")

    if expected_code == code:
        return JSONResponse({"success": True})
    return JSONResponse({"success": False})

# ✅ Қолданушыны тіркеу
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

    if not expected_code or sms_code != expected_code:
        return JSONResponse({"ok": False, "msg": "❌ Код дұрыс емес"}, status_code=400)

    query = users.insert().values(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        password=password,
        created_at=datetime.utcnow()
    )
    await database.execute(query)
    print("✅ Пайдаланушы тіркелді:", phone)
    return JSONResponse({"ok": True, "msg": "✅ Пайдаланушы тіркелді!"})

# ✅ Құпиясөзді жаңарту (reset)
@app.post("/reset_password")
async def reset_password(
    phone: str = Form(...),
    password: str = Form(...)
):
    cleaned = clean_phone(phone)

    # Тексерілмеген нөмір — қауіпсіздік
    if cleaned not in sms_codes:
        return JSONResponse({"ok": False, "msg": "Код тексерілмеген немесе уақыты өтті"}, status_code=400)

    query = users.update().where(users.c.phone == phone).values(password=password)
    await database.execute(query)
    print(f"🔐 Құпиясөз жаңартылды: {phone}")
    return JSONResponse({"ok": True, "msg": "Құпиясөз сәтті жаңартылды ✅"})

# 🔒 Қолданушылар тізімі (админге)
@app.get("/users{admin_code}", response_class=HTMLResponse)
async def view_all_users(request: Request, admin_code: str):
    if admin_code != "190340006343":
        return templates.TemplateResponse("user_not_found.html", {
            "request": request,
            "phone": admin_code
        })

    query = users.select().order_by(users.c.created_at.desc())
    user_list = await database.fetch_all(query)

    return templates.TemplateResponse("user_list.html", {
        "request": request,
        "users": user_list
    })

# ✅ Debug: JSON форматта қолданушылар
@app.get("/debug-users")
async def debug_users():
    query = users.select().order_by(users.c.created_at.desc())
    result = await database.fetch_all(query)
    return [dict(u) for u in result]
