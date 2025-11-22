# Biblioteka Miejska - System Zarządzania z AI Rekomendacjami

System zarządzania biblioteką miejską z inteligentnym systemem rekomendacji książek opartym na AI.

## 📚 Opis projektu

Aplikacja webowa dla biblioteki miejskiej umożliwiająca:
- Przeglądanie i wyszukiwanie książek
- Wypożyczanie i rezerwacje książek
- Recenzje i oceny książek
- **Inteligentne rekomendacje książek** oparte na:
  - Historii czytania użytkownika
  - Ocenach i recenzjach
  - Preferencjach gatunkowych
  - Algorytmach collaborative filtering i content-based filtering

## 🏗️ Architektura

### Backend
- **Framework**: FastAPI (Python)
- **Baza danych**: MongoDB
- **Autentykacja**: JWT
- **AI/ML**: scikit-learn, pandas, numpy

### Frontend
- **Framework**: React
- **UI Library**: Material-UI (MUI)
- **Routing**: React Router
- **HTTP Client**: Axios

## 📋 Wymagania

### Backend
- Python 3.10+
- MongoDB 5.0+
- pip

### Frontend
- Node.js 16+
- npm lub yarn

## 🚀 Szybki start

### 1. Klonowanie repozytorium

```bash
git clone <repository-url>
cd BIBLIOTEKA
```

### 2. Uruchomienie MongoDB

**Windows:**
```bash
net start MongoDB
```

**Linux/Mac:**
```bash
sudo systemctl start mongod
```

Lub pobierz MongoDB Community Server: https://www.mongodb.com/try/download/community

### 3. Konfiguracja Backendu

```bash
cd backend

# Utwórz środowisko wirtualne
python -m venv venv

# Aktywuj środowisko
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Zainstaluj zależności
pip install -r requirements.txt

# Skonfiguruj zmienne środowiskowe
cp .env.example .env
# Edytuj .env i zmień SECRET_KEY!

# Uruchom serwer
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend będzie dostępny pod: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/v1/docs
- ReDoc: http://localhost:8000/v1/redoc

### 4. Konfiguracja Frontendu

W nowym terminalu:

```bash
cd frontend

# Zainstaluj zależności
npm install

# Uruchom aplikację
npm start
```

Frontend będzie dostępny pod: http://localhost:3000

## 📁 Struktura projektu

```
BIBLIOTEKA/
├── backend/
│   ├── app/
│   │   ├── models/          # Modele danych (User, Book, Review, Loan)
│   │   ├── routes/          # Endpointy API
│   │   ├── services/        # Logika biznesowa i algorytmy AI
│   │   ├── utils/           # Narzędzia pomocnicze (security, etc.)
│   │   ├── config.py        # Konfiguracja
│   │   ├── database.py      # Połączenie z MongoDB
│   │   └── main.py          # Główny plik aplikacji
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/      # Komponenty React
│   │   ├── pages/           # Strony aplikacji
│   │   ├── context/         # Context API (AuthContext)
│   │   ├── services/        # Komunikacja z API
│   │   ├── App.js
│   │   └── index.js
│   ├── package.json
│   └── README.md
└── README.md
```

## 🔑 Funkcjonalności

### ✅ Zaimplementowane:
- Rejestracja i autentykacja użytkowników (JWT)
- Przeglądanie katalogu książek
- Wyszukiwanie książek (tytuł, autor, opis)
- Responsywny interfejs użytkownika

### 🔄 W trakcie implementacji:
- System wypożyczeń
- Recenzje i oceny książek
- Panel administratora
- **System rekomendacji AI**:
  - Collaborative Filtering
  - Content-Based Filtering
  - Hybrydowe podejście

### 📅 Planowane:
- Rezerwacje książek
- Powiadomienia o dostępności
- Statystyki i raporty
- Integracja z systemem bibliotecznym
- Export/import danych

## 🧪 Testowanie API

### Przykładowe wywołania:

#### Rejestracja użytkownika
```bash
curl -X POST "http://localhost:8000/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jan.kowalski@example.com",
    "username": "jkowalski",
    "password": "SecurePassword123!",
    "full_name": "Jan Kowalski"
  }'
```

#### Logowanie
```bash
curl -X POST "http://localhost:8000/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=jkowalski&password=SecurePassword123!"
```

#### Pobranie listy książek
```bash
curl -X GET "http://localhost:8000/v1/books/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 📊 Baza danych

### Kolekcje MongoDB:

1. **users** - Użytkownicy systemu
2. **books** - Katalog książek
3. **reviews** - Recenzje książek
4. **loans** - Historia wypożyczeń

### Przykładowe dane testowe

Możesz dodać przykładowe dane przez API lub bezpośrednio w MongoDB.

## 🔒 Bezpieczeństwo

- Hasła są hashowane używając bcrypt
- Autentykacja JWT z tokenami wygasającymi
- CORS skonfigurowany dla określonych domen
- Walidacja danych wejściowych przez Pydantic

## 🐛 Troubleshooting

### Backend nie startuje
- Sprawdź czy MongoDB jest uruchomione
- Sprawdź czy port 8000 nie jest zajęty
- Sprawdź czy wszystkie zależności są zainstalowane

### Frontend nie łączy się z API
- Sprawdź czy backend jest uruchomiony
- Sprawdź konfigurację CORS w backend/.env
- Sprawdź adres API w frontend/src/services/api.js

### Błędy MongoDB
- Sprawdź czy MongoDB działa: `mongosh`
- Sprawdź logi MongoDB
- Sprawdź connection string w .env

## 📚 Technologie

### Backend:
- FastAPI - nowoczesny framework web
- Motor - asynchroniczny driver MongoDB
- Pydantic - walidacja danych
- PassLib - haszowanie haseł
- Python-Jose - JWT
- scikit-learn - algorytmy ML
- pandas, numpy - przetwarzanie danych

### Frontend:
- React 18
- Material-UI (MUI)
- React Router v6
- Axios
- Context API

## 🤝 Wkład w projekt

1. Fork repozytorium
2. Utwórz branch z feature (`git checkout -b feature/AmazingFeature`)
3. Commit zmian (`git commit -m 'Add some AmazingFeature'`)
4. Push do brancha (`git push origin feature/AmazingFeature`)
5. Otwórz Pull Request

## 📝 Licencja

MIT License - zobacz plik LICENSE

## 👥 Autorzy

Ten projekt został stworzony jako praca inżynierska na temat zastosowania AI w systemach bibliotecznych.

## 📧 Kontakt

W razie pytań lub problemów, proszę o kontakt lub utworzenie Issue na GitHub.

---

**Powodzenia z uruchomieniem systemu! 📖**
