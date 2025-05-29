from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from database import database, users, metadata
import sqlalchemy
import random
import requests

app = FastAPI()

# PostgreSQL байланысын бастау
engine = sqlalchemy.create_engine(str(database.url))
metadata.create_all(engine)
templates = Jinja2Templates(directory="templates")

# smsc.kz параметрлері
SMS_LOGIN = "Ahan1992"
SMS_PASSWORD = "Ahan5250!"

# Уақытша SMS кодтар
sms_codes = {}

# Телефонды тазалау
def clean_phone(phone: str) -> str:
    phone = phone.replace("+7", "7")
    return phone.replace("(", "").replace(")", "").replace(" ", "").replace("-", "")

# База қосу/ажырату
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

# Код жіберу
@app.post("/send_code")
async def send_code(phone: str = Form(...)):
    cleaned = clean_phone(phone)
    code = str(random.randint(100000, 999999))
    sms_codes[cleaned] = code

    print(f"[SMS] Код {code} жіберілді: {cleaned}")

    url = f"https://smsc.kz/sys/send.php?login={SMS_LOGIN}&psw={SMS_PASSWORD}&phones={cleaned}&mes=Код:%20{code}&fmt=3"
    response = requests.get(url)

    if response.status_code == 200:
        return JSONResponse({"ok": True, "msg": "Код жіберілді ✅"})
    else:
        return JSONResponse({"ok": False, "msg": "Қате: код жіберілмеді ❌"}, status_code=500)

# Кодты тексеру
@app.post("/verify_code")
async def verify_code(phone: str = Form(...), code: str = Form(...)):
    cleaned = clean_phone(phone)
    expected_code = sms_codes.get(cleaned)

    print(f"[VERIFY] Күтілген код: {expected_code}, келген код: {code}, номер: {cleaned}")

    if expected_code == code:
        return JSONResponse({"success": True})
    return JSONResponse({"success": False})

# Пайдаланушыны тіркеу
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

    print(f"[REGISTER] Күтілген код: {expected_code}, енгізілген код: {sms_code}, номер: {cleaned}")

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

# 🔍 Барлық қолданушыларды көру (тек админ коды арқылы)
@app.get("/users{admin_code}", response_class=HTMLResponse)
async def view_all_users(request: Request, admin_code: str):
    if admin_code != "190340006343":
        return templates.TemplateResponse("user_not_found.html", {
            "request": request,
            "phone": admin_code
        })

    query = users.select()
    user_list = await database.fetch_all(query)

    return templates.TemplateResponse("user_list.html", {
        "request": request,
        "users": user_list
    })
