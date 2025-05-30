# 🔝 Файлдың ең басы
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from datetime import datetime
import sqlalchemy
import random
import requests
import os

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

    query = users.select().order_by(users.c.created_at.desc())
    user_list = await database.fetch_all(query)

    return templates.TemplateResponse("user_list.html", {
        "request": request,
        "users": user_list
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

    # 1. Дәл телефонмен іздеу
    query = users.select().where(users.c.phone == phone)
    user = await database.fetch_one(query)

    # 2. Егер табылмаса — тазаланған нұсқамен
    if not user:
        query = users.select().where(users.c.phone == cleaned)
        user = await database.fetch_one(query)

    # 3. Нәтиже
    name = user["first_name"] if user else "Қонақ"

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "name": name
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
        query = users.select().where(users.c.phone == cleaned)
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

        # Телефонды тазалау
        cleaned = phone.replace("+7", "7").replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
        print("📞 Тазаланған номер:", cleaned)

        # Қолданушыны екі форматпен іздеу
        query = users.select().where((users.c.phone == cleaned) | (users.c.phone == phone))
        user = await database.fetch_one(query)

        if not user:
            print("❌ Қолданушы табылмады")
            return JSONResponse({"ok": False, "msg": "Қолданушы табылмады"}, status_code=400)

        user_id = user["id"]
        print("👤 Қолданушы ID:", user_id)

        # Бұрын тіркелген бе?
        check_query = text("SELECT 1 FROM kaspi_shops WHERE login = :login")
        exists = await database.fetch_one(check_query, {"login": login})
        if exists:
            print("⚠️ Kaspi логин бұрын тіркелген")
            return JSONResponse({"ok": False, "msg": "❌ Бұл Kaspi логин бұрын тіркелген"})

        # 📝 Уақытша файл жасау
        import uuid, subprocess, os
        cred_file = f"temp_{uuid.uuid4().hex}.txt"
        with open(cred_file, "w", encoding="utf-8") as f:
            f.write(f"{login}\n{password}")

        print("📤 get_shop_name.py шақырылуда...")

        # Скриптті орындау
        result = subprocess.run(
            ["python", "get_shop_name.py", cred_file],
            capture_output=True,
            text=True,
            timeout=40
        )
        os.remove(cred_file)

        print("📥 stdout:", result.stdout)
        print("📥 stderr:", result.stderr)

        if result.returncode != 0:
            print("❌ Kaspi жүйесіне кіру мүмкін болмады")
            return JSONResponse({"ok": False, "msg": "Kaspi жүйесіне кіру мүмкін болмады"})

        # 🏬 Магазин атауын табу
        shop_name = None
        for line in result.stdout.splitlines():
            if "🏬 Магазин атауы:" in line:
                shop_name = line.split(":", 1)[1].strip()
                break

        if not shop_name:
            print("❌ Магазин атауы табылмады")
            return JSONResponse({"ok": False, "msg": "Магазин атауы табылмады"}, status_code=500)

        # 💾 Базаға жазу
        insert_query = text("""
            INSERT INTO kaspi_shops (user_id, shop_name, login, password, created_at)
            VALUES (:user_id, :shop_name, :login, :password, NOW())
        """)
        await database.execute(insert_query, {
            "user_id": user_id,
            "shop_name": shop_name,
            "login": login,
            "password": password
        })

        print("✅ Магазин қосылды:", shop_name)
        return JSONResponse({"ok": True, "name": shop_name})

    except Exception as e:
        print("❌ /add_kaspi_shop ішінде қате:", str(e))
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)
