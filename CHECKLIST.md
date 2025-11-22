# ✅ Checklista uruchomienia projektu

## Przed rozpoczęciem

- [ ] Zainstalowano Python 3.10+
- [ ] Zainstalowano Node.js 16+
- [ ] Zainstalowano MongoDB 5.0+
- [ ] MongoDB jest uruchomione i działa
- [ ] VS Code jest otwarty z folderem BIBLIOTEKA

---

## Backend Setup

- [ ] Terminal otwarty w folderze `backend/`
- [ ] Utworzono środowisko wirtualne (`python -m venv venv`)
- [ ] Aktywowano środowisko wirtualne (widzę `(venv)`)
- [ ] Zainstalowano zależności (`pip install -r requirements.txt`)
- [ ] Skopiowano `.env.example` do `.env`
- [ ] Zmieniono `SECRET_KEY` w pliku `.env`
- [ ] Uruchomiono `python init_db.py` (baza zainicjalizowana)
- [ ] Backend uruchomiony (`python -m uvicorn app.main:app --reload`)
- [ ] http://localhost:8000 działa ✅
- [ ] http://localhost:8000/v1/docs pokazuje API docs ✅

---

## Frontend Setup

- [ ] Otwarto NOWY terminal (backend nadal działa!)
- [ ] Terminal w folderze `frontend/`
- [ ] Zainstalowano zależności (`npm install`)
- [ ] Frontend uruchomiony (`npm start`)
- [ ] http://localhost:3000 otwiera się automatycznie ✅
- [ ] Strona się ładuje bez błędów ✅

---

## Testy funkcjonalne

- [ ] Widzę stronę główną biblioteki
- [ ] Mogę kliknąć "Zarejestruj się"
- [ ] Mogę się zalogować testowym kontem (admin/admin123)
- [ ] Po zalogowaniu widzę "Witaj" w nawigacji
- [ ] Mogę przejść do "Katalog Książek"
- [ ] Widzę listę książek
- [ ] Wyszukiwanie działa
- [ ] Mogę się wylogować

---

## Stan terminali

✅ Terminal 1: Backend
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

✅ Terminal 2: Frontend
```
Compiled successfully!

You can now view biblioteka-frontend in the browser.

  Local:            http://localhost:3000
```

---

## Jeśli coś nie działa

### Backend nie startuje
1. [ ] Sprawdź czy środowisko wirtualne jest aktywne
2. [ ] Sprawdź czy wszystkie pakiety się zainstalowały
3. [ ] Sprawdź czy MongoDB działa (`mongosh`)
4. [ ] Sprawdź logi w terminalu backendu

### Frontend nie startuje
1. [ ] Sprawdź czy `node_modules` istnieje
2. [ ] Spróbuj `npm install` ponownie
3. [ ] Sprawdź czy port 3000 nie jest zajęty
4. [ ] Sprawdź logi w terminalu frontendu

### CORS / Połączenie z API
1. [ ] Backend działa na porcie 8000?
2. [ ] W `.env` jest `ALLOWED_ORIGINS=http://localhost:3000`?
3. [ ] Restart backendu po zmianie `.env`

---

## 🎯 Następne kroki

Po uruchomieniu wszystkiego:

1. [ ] Zapoznaj się z API docs: http://localhost:8000/v1/docs
2. [ ] Przetestuj wszystkie funkcje w UI
3. [ ] Sprawdź dane w MongoDB (używając MongoDB Compass lub mongosh)
4. [ ] Przeczytaj dokumentację w README.md
5. [ ] Zacznij rozwijać system rekomendacji!

---

## 📝 Notatki

Data pierwszego uruchomienia: __________

Problemy napotkane: 
_________________________________________________
_________________________________________________
_________________________________________________

Rozwiązania:
_________________________________________________
_________________________________________________
_________________________________________________

---

**✅ Wszystko działa? Świetnie! Możesz zacząć pracę nad systemem! 🚀**
