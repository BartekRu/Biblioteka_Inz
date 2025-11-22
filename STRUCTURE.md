# 📁 Struktura projektu BIBLIOTEKA

```
BIBLIOTEKA/
│
├── 📄 README.md                    # Główna dokumentacja projektu
├── 📄 SETUP_GUIDE.md              # Przewodnik instalacji krok-po-kroku
├── 📄 CHECKLIST.md                # Checklista uruchomienia
├── 📄 .gitignore                  # Pliki ignorowane przez Git
│
├── 📂 backend/                     # Backend (Python/FastAPI)
│   ├── 📄 README.md               # Dokumentacja backendu
│   ├── 📄 requirements.txt        # Zależności Pythona
│   ├── 📄 .env.example            # Przykładowa konfiguracja
│   ├── 📄 init_db.py              # Skrypt inicjalizacji bazy
│   │
│   └── 📂 app/                     # Główna aplikacja
│       ├── 📄 __init__.py
│       ├── 📄 main.py             # 🚀 Główny plik FastAPI
│       ├── 📄 config.py           # ⚙️ Konfiguracja aplikacji
│       ├── 📄 database.py         # 💾 Połączenie z MongoDB
│       │
│       ├── 📂 models/              # 📊 Modele danych (Pydantic)
│       │   ├── 📄 __init__.py
│       │   ├── 📄 user.py         # Model użytkownika
│       │   ├── 📄 book.py         # Model książki
│       │   ├── 📄 review.py       # Model recenzji
│       │   └── 📄 loan.py         # Model wypożyczenia
│       │
│       ├── 📂 routes/              # 🛣️ Endpointy API
│       │   ├── 📄 __init__.py
│       │   ├── 📄 auth.py         # Autentykacja (login, register)
│       │   └── 📄 books.py        # Zarządzanie książkami
│       │
│       ├── 📂 services/            # 🔧 Logika biznesowa
│       │   └── (będzie dodane)
│       │
│       └── 📂 utils/               # 🛠️ Narzędzia pomocnicze
│           ├── 📄 __init__.py
│           └── 📄 security.py     # JWT, hashowanie haseł
│
└── 📂 frontend/                    # Frontend (React)
    ├── 📄 README.md               # Dokumentacja frontendu
    ├── 📄 package.json            # Zależności Node.js
    │
    ├── 📂 public/                  # Pliki publiczne
    │   └── 📄 index.html          # Główny HTML
    │
    └── 📂 src/                     # Kod źródłowy React
        ├── 📄 index.js            # 🚀 Punkt wejścia React
        ├── 📄 index.css           # Globalne style
        ├── 📄 App.js              # 🎯 Główny komponent + routing
        │
        ├── 📂 components/          # ⚛️ Komponenty wielokrotnego użytku
        │   └── 📄 Navbar.js       # Nawigacja
        │
        ├── 📂 pages/               # 📄 Strony aplikacji
        │   ├── 📄 Home.js         # Strona główna
        │   ├── 📄 Login.js        # Logowanie
        │   ├── 📄 Register.js     # Rejestracja
        │   └── 📄 Books.js        # Katalog książek
        │
        ├── 📂 context/             # 🌐 Context API (stan globalny)
        │   └── 📄 AuthContext.js  # Kontekst autentykacji
        │
        ├── 📂 services/            # 🔌 Komunikacja z API
        │   └── 📄 api.js          # Axios + endpointy
        │
        └── 📂 utils/               # 🛠️ Narzędzia pomocnicze
            └── (będzie dodane)
```

---

## 🔑 Kluczowe pliki do edycji

### Backend

**Konfiguracja:**
- `backend/.env` - Zmienne środowiskowe (MongoDB, JWT, CORS)
- `backend/app/config.py` - Ustawienia aplikacji

**Modele danych:**
- `backend/app/models/user.py` - Użytkownicy
- `backend/app/models/book.py` - Książki
- `backend/app/models/review.py` - Recenzje
- `backend/app/models/loan.py` - Wypożyczenia

**API Endpointy:**
- `backend/app/routes/auth.py` - Rejestracja, logowanie
- `backend/app/routes/books.py` - CRUD książek

### Frontend

**Routing i główna logika:**
- `frontend/src/App.js` - Routing i tema MUI

**Strony:**
- `frontend/src/pages/Home.js` - Strona główna
- `frontend/src/pages/Books.js` - Lista książek
- `frontend/src/pages/Login.js` - Logowanie
- `frontend/src/pages/Register.js` - Rejestracja

**Stan globalny:**
- `frontend/src/context/AuthContext.js` - Autentykacja

**API:**
- `frontend/src/services/api.js` - Endpointy backendu

---

## 🎯 Gdzie dodawać nowe funkcje?

### Nowy endpoint API (backend)
1. Model: `backend/app/models/nazwa.py`
2. Route: `backend/app/routes/nazwa.py`
3. Rejestracja w `backend/app/main.py`

### Nowa strona (frontend)
1. Komponent: `frontend/src/pages/NazwaStrony.js`
2. Route w `frontend/src/App.js`
3. Link w `frontend/src/components/Navbar.js`

### System rekomendacji (docelowo)
- Backend: `backend/app/services/recommendation_service.py`
- Route: `backend/app/routes/recommendations.py`
- Frontend: `frontend/src/pages/Recommendations.js`

---

## 📊 Baza danych MongoDB

### Kolekcje:
- `users` - Użytkownicy systemu
- `books` - Katalog książek
- `reviews` - Recenzje książek
- `loans` - Historia wypożyczeń

### Narzędzia do przeglądania:
- **MongoDB Compass** (GUI): https://www.mongodb.com/products/compass
- **mongosh** (CLI): `mongosh` w terminalu

---

## 🔄 Workflow developmentu

1. **Backend:** Dodaj model → Dodaj route → Przetestuj w Swagger
2. **Frontend:** Dodaj API call → Utwórz komponent → Dodaj routing
3. **Test:** Przetestuj funkcjonalność end-to-end

---

**📚 Wszystko gotowe do rozpoczęcia pracy!**
