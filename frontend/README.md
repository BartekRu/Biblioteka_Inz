# Frontend - Biblioteka

Frontend aplikacji biblioteki miejskiej zbudowany w React z Material-UI.

## Wymagania

- Node.js 16+
- npm lub yarn

## Instalacja

### 1. Zainstaluj zależności

```bash
npm install
```

lub

```bash
yarn install
```

## Uruchamianie

### Tryb deweloperski

```bash
npm start
```

Aplikacja otworzy się automatycznie w przeglądarce pod adresem: http://localhost:3000

### Build produkcyjny

```bash
npm run build
```

Zbudowana aplikacja znajdzie się w folderze `build/`

## Struktura projektu

```
frontend/
├── public/
│   └── index.html           # Główny plik HTML
├── src/
│   ├── components/          # Komponenty wielokrotnego użytku
│   │   └── Navbar.js
│   ├── pages/               # Strony aplikacji
│   │   ├── Home.js
│   │   ├── Login.js
│   │   ├── Register.js
│   │   └── Books.js
│   ├── context/             # React Context (stan globalny)
│   │   └── AuthContext.js
│   ├── services/            # Serwisy do komunikacji z API
│   │   └── api.js
│   ├── utils/               # Narzędzia pomocnicze
│   ├── App.js               # Główny komponent
│   ├── index.js             # Punkt wejścia
│   └── index.css            # Globalne style
├── package.json
└── README.md
```

## Funkcjonalności

### Zaimplementowane:
- ✅ Rejestracja użytkownika
- ✅ Logowanie/wylogowanie
- ✅ Przeglądanie katalogu książek
- ✅ Wyszukiwanie książek
- ✅ Responsywny design (desktop/mobile)

### W przygotowaniu:
- ⏳ Szczegóły książki
- ⏳ Wypożyczanie książek
- ⏳ Recenzje i oceny
- ⏳ System rekomendacji AI
- ⏳ Panel użytkownika
- ⏳ Panel administratora

## Konfiguracja

### API URL

Domyślnie aplikacja łączy się z API pod adresem `http://localhost:8000`

Aby zmienić adres API, edytuj plik `src/services/api.js`:

```javascript
const API_BASE_URL = 'http://localhost:8000/v1';
```

## Komponenty

### Navbar
Nawigacja strony z responsywnym menu mobilnym.

### AuthContext
Zarządza stanem autentykacji użytkownika w całej aplikacji.

### Pages
- **Home**: Strona główna z przedstawieniem funkcjonalności
- **Login**: Formularz logowania
- **Register**: Formularz rejestracji
- **Books**: Katalog książek z wyszukiwaniem

## Stylowanie

Aplikacja używa Material-UI (MUI) jako głównej biblioteki komponentów.

Tema jest skonfigurowany w `App.js` i może być dostosowany:

```javascript
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});
```

## Troubleshooting

### Port 3000 jest zajęty

Jeśli port 3000 jest zajęty, możesz uruchomić aplikację na innym porcie:

```bash
PORT=3001 npm start
```

### Błąd CORS

Upewnij się, że backend ma prawidłowo skonfigurowane CORS:
- Sprawdź czy frontend URL jest w `ALLOWED_ORIGINS` w `.env` backendu

### Błąd połączenia z API

1. Sprawdź czy backend jest uruchomiony na `http://localhost:8000`
2. Sprawdź konfigurację w `src/services/api.js`
3. Sprawdź console przeglądarki dla szczegółowych błędów

## Rozwój

### Dodawanie nowych stron

1. Utwórz nowy komponent w `src/pages/`
2. Dodaj routing w `src/App.js`:

```javascript
import NewPage from './pages/NewPage';

// W komponencie App
<Route path="/new-page" element={<NewPage />} />
```

### Dodawanie nowych API endpoints

Edytuj `src/services/api.js` i dodaj nowe metody:

```javascript
export const newAPI = {
  getData: () => api.get('/new-endpoint'),
  postData: (data) => api.post('/new-endpoint', data)
};
```

## Testowanie

```bash
npm test
```

## Licencja

MIT
