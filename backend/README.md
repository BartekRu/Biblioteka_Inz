# Backend - Biblioteka API

Backend aplikacji biblioteki miejskiej oparty na FastAPI i Python.

## Wymagania

- Python 3.10+
- MongoDB 5.0+
- pip

## Instalacja

### 1. Utwórz środowisko wirtualne

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 2. Zainstaluj zależności

```bash
pip install -r requirements.txt
```

### 3. Skonfiguruj MongoDB

Upewnij się, że MongoDB jest uruchomione lokalnie na porcie 27017.

**Windows:**
```bash
# Uruchom MongoDB jako usługę
net start MongoDB
```

**Linux/Mac:**
```bash
# Uruchom MongoDB
sudo systemctl start mongod
```

Lub pobierz i uruchom MongoDB Community Server ze strony: https://www.mongodb.com/try/download/community

### 4. Skonfiguruj zmienne środowiskowe

Skopiuj plik `.env.example` do `.env` i dostosuj konfigurację:

```bash
cp .env.example .env
```

Edytuj `.env` i zmień wartości:
```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=biblioteka
SECRET_KEY=your-secret-key-here-change-in-production  # ZMIEŃ TO!
```

## Uruchamianie

### Tryb deweloperski (z hot-reload)

```bash
# Z poziomu katalogu backend/
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Lub:

```bash
python -m app.main
```

### Tryb produkcyjny

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Dokumentacja API

Po uruchomieniu aplikacji, dokumentacja API jest dostępna pod adresami:

- **Swagger UI**: http://localhost:8000/v1/docs
- **ReDoc**: http://localhost:8000/v1/redoc

## Struktura projektu

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Główny plik aplikacji
│   ├── config.py            # Konfiguracja
│   ├── database.py          # Połączenie z MongoDB
│   ├── models/              # Modele danych (Pydantic)
│   │   ├── user.py
│   │   ├── book.py
│   │   ├── review.py
│   │   └── loan.py
│   ├── routes/              # Endpointy API
│   │   ├── auth.py
│   │   ├── books.py
│   │   ├── users.py
│   │   └── recommendations.py
│   ├── services/            # Logika biznesowa
│   │   ├── auth_service.py
│   │   └── recommendation_service.py
│   └── utils/               # Narzędzia pomocnicze
│       └── security.py
├── tests/                   # Testy
├── requirements.txt         # Zależności
└── .env                     # Zmienne środowiskowe
```

## Endpointy API

### Autentykacja
- `POST /v1/auth/register` - Rejestracja nowego użytkownika
- `POST /v1/auth/token` - Logowanie (otrzymanie tokenu JWT)
- `GET /v1/auth/me` - Informacje o zalogowanym użytkowniku

### Książki
- `GET /v1/books/` - Lista książek (z filtrowaniem)
- `GET /v1/books/{book_id}` - Szczegóły książki
- `POST /v1/books/` - Dodanie nowej książki (librarian/admin)
- `PUT /v1/books/{book_id}` - Aktualizacja książki (librarian/admin)
- `DELETE /v1/books/{book_id}` - Usunięcie książki (admin)

## Testowanie

Przykładowe wywołanie API używając curl:

```bash
# Rejestracja użytkownika
curl -X POST "http://localhost:8000/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jan.kowalski@example.com",
    "username": "jkowalski",
    "password": "SecurePassword123!",
    "full_name": "Jan Kowalski"
  }'

# Logowanie
curl -X POST "http://localhost:8000/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=jkowalski&password=SecurePassword123!"

# Pobranie listy książek (wymaga tokenu)
curl -X GET "http://localhost:8000/v1/books/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Troubleshooting

### Problem z połączeniem do MongoDB

```
Error: connection to mongodb://localhost:27017 failed
```

**Rozwiązanie:**
1. Sprawdź czy MongoDB jest uruchomione
2. Sprawdź konfigurację w pliku `.env`
3. Upewnij się, że port 27017 nie jest zajęty przez inną aplikację

### Problem z importami

```
ModuleNotFoundError: No module named 'fastapi'
```

**Rozwiązanie:**
1. Sprawdź czy środowisko wirtualne jest aktywowane
2. Zainstaluj ponownie zależności: `pip install -r requirements.txt`

## Rozwój

### Dodawanie nowych endpointów

1. Utwórz nowy plik w `app/routes/`
2. Zdefiniuj router i endpointy
3. Dodaj router w `app/main.py`

### Dodawanie nowych modeli

1. Utwórz nowy plik w `app/models/`
2. Zdefiniuj modele Pydantic
3. Zaimportuj w `app/models/__init__.py`

## Licencja

MIT
