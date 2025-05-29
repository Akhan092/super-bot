# 📲 SMS арқылы тіркелу жүйесі (FastAPI)

Бұл жоба FastAPI көмегімен пайдаланушылардың SMS-код арқылы тіркелу жүйесін іске асырады.

## 🔧 Орнату

1. `.env` файлын жасаңыз және өзіңіздің деректеріңізді толтырыңыз.
2. Қажетті тәуелділіктерді орнатыңыз:

```bash
pip install -r requirements.txt
```

3. Серверді іске қосыңыз:

```bash
uvicorn main:app --reload
```

4. Браузерде ашыңыз:

```
http://localhost:8000/register
```

## 🗃 Папка құрылымы

```
project/
│
├── main.py
├── database.py
├── requirements.txt
├── users_api_sample.py
├── .env
├── .gitignore
├── README.md
│
└── templates/
    ├── register.html
    └── index.html
```

## ✉️ SMS қызметі

Бұл жүйе [smsc.kz](https://smsc.kz) арқылы SMS код жібереді. API параметрлері `.env` ішінде сақталады.
