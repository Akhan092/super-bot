# 🔝 Файлдың ең басы
from fastapi import FastAPI, Form, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from datetime import datetime, timedelta
import sqlalchemy
import random
import requests
import uuid
import os
import subprocess
import httpx

from database import database, users, metadata, kaspi_shops  # ✅ БІР ЖОЛҒА біріктіріңіз


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

# Парольды жанарту беті	
@app.get("/forgot_password", response_class=HTMLResponse)
async def forgot_password(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

# ✅ СМС код жіберу және тіркелген нөмірді тексеру
@app.post("/send_code")
async def send_code(
    phone: str = Form(...),
    mode: str = Form("default")
):
    cleaned = clean_phone(phone)  # ✅ << ҚОСУ КЕРЕК

    if mode == "register":
        query = users.select().where(users.c.phone == phone)
        user_exists = await database.fetch_one(query)
        if user_exists:
            return JSONResponse({
                "ok": False,
                "msg": "Бұл нөмір тіркелген",
                "exists": True
            })

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
        print("📤 Textbelt request payload:", payload)
        print("📨 Textbelt response (raw):", response.text)
        data = response.json()
        print("✅ Textbelt response (parsed):", data)
    except Exception as e:
        print("❌ JSON parse error:", str(e))
        return JSONResponse({
            "ok": False,
            "msg": "Жауапты талдау қатесі",
            "error": str(e),
            "raw": response.text
        }, status_code=500)

    if data.get("success"):
        return JSONResponse({"ok": True, "msg": "Код жіберілді ✅"})
    else:
        return JSONResponse({
            "ok": False,
            "msg": data.get("error", "Қате: код жіберілмеді ❌"),
            "data": data
        }, status_code=500)
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

@app.post("/reset_password")
async def reset_password(
    phone: str = Form(...),
    password: str = Form(...)
):
    cleaned = clean_phone(phone)

    # 🔒 Егер бұл телефонмен SMS код алынбаған болса – қауіпсіздік
    if cleaned not in sms_codes:
        return JSONResponse({"ok": False, "msg": "Код тексерілмеген немесе уақыты өтті"}, status_code=400)

    # ✅ Құпиясөзді жаңарту
    query = users.update().where(users.c.phone == phone).values(password=password)
    await database.execute(query)

    print(f"🔐 Құпиясөз жаңартылды: {phone}")
    return JSONResponse({"ok": True, "msg": "Құпиясөз сәтті жаңартылды ✅"})


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

# 🔒 Қолданушылар тізімі (админге)
@app.get("/users{admin_code}", response_class=HTMLResponse)
async def view_all_users(request: Request, admin_code: str):
    if admin_code != "190340006343":
        return templates.TemplateResponse("user_not_found.html", {
            "request": request,
            "phone": admin_code
        })

    # 1. Барлық қолданушыларды алу
    query = users.select().order_by(users.c.created_at.desc())
    user_list = await database.fetch_all(query)

    enriched_users = []

    # 2. Әр қолданушыға тиесілі магазиндерді қосу
    for user in user_list:
        shop_query = kaspi_shops.select().where(kaspi_shops.c.user_id == user["id"])
        shops = await database.fetch_all(shop_query)

        enriched_users.append({
            "id": user["id"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "phone": user["phone"],
            "password": user["password"],
            "created_at": user["created_at"],
            "shops": [dict(s) for s in shops]
        })

    from datetime import timedelta  # қосылған болу керек

    return templates.TemplateResponse("user_list.html", {
        "request": request,
        "users": enriched_users,
        "timedelta": timedelta  # МІНЕ ОСЫ ЖЕРІ МАҢЫЗДЫ
    })


# ✅ created_at бағанын қосу (бір реттік)
@app.get("/add-created-at")
async def add_created_at_column():
    try:
        await database.execute(text(
            "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ))
        return {"ok": True, "msg": "✅ created_at бағаны қосылды"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, phone: str = ""):
    cleaned = clean_phone(phone)

    # 1. Қолданушыны табу
    query = users.select().where(users.c.phone == phone)
    user = await database.fetch_one(query)

    if not user:
        query = users.select().where(users.c.phone == cleaned)
        user = await database.fetch_one(query)

    if not user:
        return templates.TemplateResponse("user_not_found.html", {
            "request": request,
            "phone": phone
        })

    user_id = user["id"]
    name = user["first_name"]

    # 2. Магазиндерді жүктеу
    shop_query = kaspi_shops.select().where(kaspi_shops.c.user_id == user_id).order_by(kaspi_shops.c.created_at.desc())
    shops = await database.fetch_all(shop_query)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "name": name,
        "shops": [dict(s) for s in shops]
    })

# ✅ Debug: JSON форматта қолданушылар
@app.get("/debug-users")
async def debug_users():
    query = users.select().order_by(users.c.created_at.desc())
    result = await database.fetch_all(query)
    return [dict(u) for u in result]
@app.post("/login_check")
async def login_check(phone: str = Form(...), password: str = Form(...)):
    cleaned = clean_phone(phone)

    # Ең бірінші — іздеуді номер бойынша
    query = users.select().where(users.c.phone == phone)
    user = await database.fetch_one(query)

    # Егер табылмаса, тазаланған нұсқамен іздейміз
    if not user:
        query = users.select().where((users.c.phone == cleaned) | (users.c.phone == phone))
        user = await database.fetch_one(query)

    # Егер қолданушы жоқ болса
    if not user:
        return JSONResponse({"ok": False, "msg": "❌ Мұндай нөмір тіркелмеген"}, status_code=400)

    # Құпиясөз дұрыс па
    if user["password"] != password:
        return JSONResponse({"ok": False, "msg": "❌ Құпиясөз дұрыс емес"}, status_code=400)

    print(f"✅ Кіру сәтті: {phone}")
    return JSONResponse({"ok": True})

    query = users.select().order_by(users.c.created_at.desc())
    result = await database.fetch_all(query)
    return [dict(u) for u in result]

@app.post("/add_kaspi_shop")
async def add_kaspi_shop(
    login: str = Form(...),
    password: str = Form(...),
    phone: str = Form(...)
):
    try:
        print("🟢 /add_kaspi_shop басталды")
        print("📥 Келген мәліметтер:", login, phone)

        # 🔎 Қолданушыны іздеу
        query = users.select().where(users.c.phone == phone)
        user = await database.fetch_one(query)

        if not user:
            print("❌ Қолданушы табылмады")
            return JSONResponse({"ok": False, "msg": "Қолданушы табылмады"}, status_code=400)

        user_id = user["id"]
        print("👤 Қолданушы ID:", user_id)

        # 🔁 Бұрын тіркелген бе?
        check_query = kaspi_shops.select().where(kaspi_shops.c.login == login)
        exists = await database.fetch_one(check_query)
        if exists:
            print("⚠️ Kaspi логин бұрын тіркелген")
            return JSONResponse({"ok": False, "msg": "❌ Бұл Kaspi логин бұрын тіркелген"})

        # 🌐 Сыртқы серверге сұраныс (Kaspi ботқа)
        print("🌐 Kaspi ботқа сұраныс жіберілуде...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post("http://45.136.57.219:5000/check_kaspi", data={
                "login": login,
                "password": password
            })

        if response.status_code != 200:
            print("❌ Kaspi бот жауап бермеді")
            return JSONResponse({"ok": False, "msg": "Kaspi сервері жауап қатпады"}, status_code=500)

        data = response.json()
        if not data.get("ok"):
            print("❌ Kaspi бот қатесі:", data.get("msg"))
            return JSONResponse({"ok": False, "msg": data.get("msg", "Kaspi жауап қатесі")}, status_code=400)

        shop_name = data["shop_name"]
        merchant_id = data["merchant_id"]  # Егер жоқ болса, бос қылады
        print("✅ Kaspi боттан магазин атауы алынды:", shop_name)
        
        now = datetime.utcnow()

        # Базаға жазу
        query = kaspi_shops.insert().values(
            user_id=user_id,
            shop_name=shop_name,
            login=login,
            password=password,
            merchant_id=merchant_id,  # ✅ жаңа баған
            created_at=now
        )

        # 💾 Базаға жазу
        await database.execute(query)
        
        # Нақты created_at мәнін база ішінен аламыз
        select_query = kaspi_shops.select().where(
            (kaspi_shops.c.user_id == user_id) &
            (kaspi_shops.c.login == login)
        ).order_by(kaspi_shops.c.created_at.desc())
        
        shop_row = await database.fetch_one(select_query)
        
        return JSONResponse({
            "ok": True,
            "name": shop_name,
            "login": login,
            "password": password,
            "merchant_id": merchant_id,
            "created_at": shop_row["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
            "expires": (shop_row["created_at"] + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        })

    except Exception as e:
        print("❌ /add_kaspi_shop ішінде қате:", str(e))
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

@app.get("/get_kaspi_shops")
async def get_kaspi_shops(phone: str = Query(...)):
    # 🔍 Қолданушыны телефон арқылы табу
    query = users.select().where(users.c.phone == phone)
    user = await database.fetch_one(query)

    if not user:
        return JSONResponse({"ok": False, "msg": "Қолданушы табылмады"}, status_code=400)

    user_id = user["id"]

    # 🔄 Kaspi магазиндерін осы қолданушыға қарай жүктеу
    shop_query = kaspi_shops.select().where(kaspi_shops.c.user_id == user_id).order_by(kaspi_shops.c.created_at.desc())
    result = await database.fetch_all(shop_query)

    shops = []
    for row in result:
        shops.append({
            "id": row["id"],
            "name": row["shop_name"],
            "expires": (row["created_at"] + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        })

    return shops

@app.post("/delete_kaspi_shop")
async def delete_kaspi_shop(name: str = Form(...), phone: str = Form(...)):
    query = users.select().where(users.c.phone == phone)
    user = await database.fetch_one(query)
    if not user:
        return JSONResponse({"ok": False, "msg": "Қолданушы табылмады"}, status_code=400)

    delete_query = kaspi_shops.delete().where(
        (kaspi_shops.c.shop_name == name) & (kaspi_shops.c.user_id == user["id"])
    )
    await database.execute(delete_query)
    return {"ok": True}

@app.get("/add-merchant-id-column")
async def add_merchant_id_column():
    try:
        await database.execute(text(
            "ALTER TABLE kaspi_shops ADD COLUMN merchant_id TEXT"
        ))
        return {"ok": True, "msg": "✅ merchant_id бағаны қосылды"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/add-merchant-id")
async def add_merchant_id_column():
    try:
        await database.execute(text(
            "ALTER TABLE kaspi_shops ADD COLUMN IF NOT EXISTS merchant_id VARCHAR"
        ))
        return {"ok": True, "msg": "✅ merchant_id бағаны қосылды"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
