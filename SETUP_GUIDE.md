# 🚀 Przewodnik instalacji - Krok po kroku

## Wymagania wstępne

✅ Python 3.10 lub nowszy  
✅ Node.js 16 lub nowszy  
✅ MongoDB 5.0 lub nowszy  
✅ VS Code (lub inny edytor)

---

## Krok 1: Instalacja MongoDB

### Windows:
1. Pobierz MongoDB Community Server: https://www.mongodb.com/try/download/community
2. Zainstaluj z domyślnymi ustawieniami
3. MongoDB uruchomi się automatycznie jako usługa

### Sprawdzenie czy MongoDB działa:
```bash
mongosh
```
Jeśli widzisz terminal MongoDB - wszystko działa! Wpisz `exit` aby wyjść.

---

## Krok 2: Backend (Python/FastAPI)

### A. Otwórz terminal w VS Code

W VS Code:
- Menu → Terminal → New Terminal
- Lub skrót: `Ctrl + `` (backtick)

### B. Przejdź do folderu backend

```bash
cd BIBLIOTEKA/backend
```

### C. Utwórz środowisko wirtualne

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Po aktywacji zobaczysz `(venv)` przed promptem.

### D. Zainstaluj zależności

```bash
pip install -r requirements.txt
```

To potrwa ~2-3 minuty. Poczekaj aż się zakończy.

### E. Skonfiguruj zmienne środowiskowe

1. Skopiuj plik konfiguracyjny:
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

2. Edytuj `.env` i **KONIECZNIE zmień SECRET_KEY**:
```env
SECRET_KEY=tutaj-wstaw-jakis-losowy-ciag-znakow-min-32-znaki
```

### F. Zainicjuj bazę danych przykładowymi danymi

```bash
python init_db.py
```

Zobaczysz dane logowania do systemu.

### G. Uruchom backend

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**✅ Backend działa!** Otwórz: http://localhost:8000/v1/docs

---

## Krok 3: Frontend (React)

### A. Otwórz NOWY terminal

W VS Code:
- Kliknij `+` w panelu terminali (góra)
- Lub: Terminal → New Terminal

**Ważne:** NIE zamykaj terminala z backendem!

### B. Przejdź do folderu frontend

```bash
cd BIBLIOTEKA/frontend
```

### C. Zainstaluj zależności

```bash
npm install
```

To potrwa ~3-5 minut przy pierwszym razie.

### D. Uruchom frontend

```bash
npm start
```

Przeglądarka otworzy się automatycznie na: http://localhost:3000

**✅ Frontend działa!**

---

## 🎉 Gotowe!

Teraz powinieneś mieć:

1. **Backend** działający na: http://localhost:8000
   - API Docs: http://localhost:8000/v1/docs
   
2. **Frontend** działający na: http://localhost:3000

3. **Dwa terminale** otwarte w VS Code:
   - Terminal 1: Backend (venv aktywne)
   - Terminal 2: Frontend (npm start)

---

## 🔐 Testowe konta

### Administrator
- **Login:** admin
- **Hasło:** admin123

### Bibliotekarz
- **Login:** bibliotekarz
- **Hasło:** bibliotekarz123

### Użytkownik
- **Login:** uzytkownik
- **Hasło:** uzytkownik123

---

## ❗ Rozwiązywanie problemów

### Backend nie startuje

**Problem:** `ModuleNotFoundError: No module named 'fastapi'`  
**Rozwiązanie:** Sprawdź czy środowisko wirtualne jest aktywowane (widzisz `(venv)`?)

**Problem:** `Error connecting to MongoDB`  
**Rozwiązanie:** 
1. Sprawdź czy MongoDB działa: `mongosh`
2. Uruchom MongoDB: `net start MongoDB` (Windows)

### Frontend nie startuje

**Problem:** `command not found: npm`  
**Rozwiązanie:** Zainstaluj Node.js ze strony: https://nodejs.org/

**Problem:** Port 3000 jest zajęty  
**Rozwiązanie:** `PORT=3001 npm start`

### CORS Error w przeglądarce

**Rozwiązanie:** 
1. Sprawdź czy backend działa
2. Sprawdź `.env` w backendzie - czy jest `ALLOWED_ORIGINS=http://localhost:3000`

---

## 🛑 Zatrzymywanie aplikacji

### Zatrzymaj backend:
W terminalu z backendem: `Ctrl + C`

### Zatrzymaj frontend:
W terminalu z frontendem: `Ctrl + C`

### Dezaktywuj środowisko wirtualne:
```bash
deactivate
```

---

## ▶️ Ponowne uruchomienie

### Backend:
```bash
cd BIBLIOTEKA/backend
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux/Mac
python -m uvicorn app.main:app --reload
```

### Frontend:
```bash
cd BIBLIOTEKA/frontend
npm start
```

---

## 📚 Następne kroki

1. Zaloguj się na konto testowe
2. Przeglądaj katalog książek
3. Testuj wyszukiwanie
4. Sprawdź API w Swagger: http://localhost:8000/v1/docs

---

## 🆘 Pomoc

Jeśli masz problemy:
1. Przeczytaj README.md w głównym folderze
2. Sprawdź README.md w folderach backend/ i frontend/
3. Sprawdź logi w terminalach
4. Upewnij się że MongoDB działa

**Powodzenia! 🚀**
