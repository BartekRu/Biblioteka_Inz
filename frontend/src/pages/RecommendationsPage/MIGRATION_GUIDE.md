# 🔄 Migration Guide - RecommendationsPage Refactor

## Przegląd zmian

### Przed (stary kod)
```
RecommendationsPage.jsx (1500+ linii)
├── Wszystkie komponenty w jednym pliku
├── Zagnieżdżone style inline
├── Powtarzający się kod
└── Trudny w utrzymaniu
```

### Po (nowy kod)
```
recommendations/
├── RecommendationsPage.jsx (300 linii - orkiestrator)
├── components/ (9 sekcji)
├── styles/theme.js (centralne style)
└── utils/bookHelpers.js (funkcje pomocnicze)
```

---

## Krok po kroku: Migracja

### 📦 KROK 1: Backup oryginalnego kodu

```bash
# Stwórz backup
cp src/pages/recommendations/RecommendationsPage.jsx \
   src/pages/recommendations/RecommendationsPage.OLD.jsx

# Lub całego folderu
cp -r src/pages/recommendations src/pages/recommendations.backup
```

---

### 📂 KROK 2: Skopiuj nową strukturę

```bash
# Skopiuj wszystkie pliki z recommendations-refactor
cp -r recommendations-refactor/* src/pages/recommendations/
```

**Struktura po skopiowaniu:**
```
src/pages/recommendations/
├── RecommendationsPage.jsx (nowy)
├── RecommendationsPage.OLD.jsx (backup)
├── components/
│   ├── shared/
│   ├── controls/
│   ├── sectionA/
│   ├── sectionB/
│   └── sectionC/
├── styles/
│   └── theme.js
├── utils/
│   └── bookHelpers.js
├── index.js
├── README.md
├── api-examples.js
└── migration-guide.md (ten plik)
```

---

### 🔧 KROK 3: Zaktualizuj importy w API service

#### Przed (jeśli używałeś)
```jsx
// services/api.js (przykład)
export const recommendationsAPI = {
  getUserRecommendations: async () => {
    // ...
  },
};
```

#### Po (dodaj nowe endpointy)
```jsx
// services/api.js
export const recommendationsAPI = {
  // ✅ Istniejące (już działają)
  getUserLightGCN: async (limit, offset, useMmr, lambda, enforceAuthorLimit, maxPerAuthor) => {
    const params = new URLSearchParams({
      limit: limit?.toString() || '30',
      offset: offset?.toString() || '0',
      use_mmr: useMmr?.toString() || 'true',
      lambda_param: lambda?.toString() || '0.7',
      enforce_author_limit: enforceAuthorLimit?.toString() || 'true',
      max_per_author: maxPerAuthor?.toString() || '2',
    });
    const response = await fetch(`/api/recommendations/lightgcn?${params}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    return response.json();
  },

  reportInteraction: async (bookId, interactionType, metadata = {}) => {
    const response = await fetch('/api/interactions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify({
        book_id: bookId,
        interaction_type: interactionType,
        metadata,
      }),
    });
    return response.json();
  },

  // 🆕 Nowe endpointy (do zaimplementowania w backendzie)
  getBecauseYouBorrowed: async () => {
    const response = await fetch('/api/recommendations/because-borrowed', {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    return response.json();
  },

  getGenreRecommendations: async () => {
    const response = await fetch('/api/recommendations/by-genre', {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    return response.json();
  },

  getAuthorRecommendations: async () => {
    const response = await fetch('/api/recommendations/by-author', {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    return response.json();
  },

  getSimilarReadersBooks: async () => {
    const response = await fetch('/api/recommendations/similar-readers', {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    return response.json();
  },

  getNewArrivals: async () => {
    const response = await fetch('/api/recommendations/new-arrivals', {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    return response.json();
  },

  getLibrarianPicks: async () => {
    const response = await fetch('/api/recommendations/librarian-picks', {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    return response.json();
  },

  getModelMetrics: async () => {
    const response = await fetch('/api/recommendations/metrics', {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    return response.json();
  },

  getCategories: async () => {
    // Jeśli istnieje
    const response = await fetch('/api/books/categories', {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    return response.json();
  },

  getKnownAuthors: async () => {
    // Jeśli istnieje
    const response = await fetch('/api/recommendations/known-authors', {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    return response.json();
  },

  getDiscoveryQueue: async () => {
    // Jeśli istnieje
    const response = await fetch('/api/recommendations/discovery-queue', {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    return response.json();
  },
};

// Helper function
function getToken() {
  return localStorage.getItem('authToken') || '';
}
```

---

### 🎨 KROK 4: Sprawdź ścieżki importów

W głównym pliku aplikacji (`App.jsx` lub routing):

#### Przed
```jsx
import RecommendationsPage from './pages/recommendations/RecommendationsPage';
```

#### Po (to samo!)
```jsx
import RecommendationsPage from './pages/recommendations/RecommendationsPage';
// lub
import { RecommendationsPage } from './pages/recommendations';
```

Ścieżki importu **nie zmieniają się** - używasz tego samego komponentu!

---

### 🧪 KROK 5: Testowanie

#### 5.1 Sprawdź podstawowe ładowanie
```bash
npm start
# lub
yarn start
```

Otwórz `/recommendations` w przeglądarce.

#### 5.2 Sprawdź console
Otwórz DevTools (F12) → Console

**Oczekiwane logi:**
```
🔄 Fetching recommendations with MMR: { mmrEnabled: true, lambdaValue: 0.7, authorLimit: true }
✅ Loaded 30 top recommendations
📊 Diversity metrics: { unique_authors: 15, unique_genres: 8, ... }
```

**Możliwe błędy:**
```
❌ Error fetching recommendations: 404 Not Found
```
→ Backend nie ma jeszcze nowych endpointów (to OK, sekcje po prostu się nie pokażą)

#### 5.3 Sprawdź czy sekcje się renderują

Powinny być widoczne (w kolejności):
1. ✅ MMR Control Panel (zawsze)
2. ✅ Top Recommendations (sekcja A)
3. ❓ Because You Borrowed (jeśli backend wspiera)
4. ❓ Genre Recommendations (jeśli backend wspiera)
5. ... itd.

**Jeśli sekcja nie pojawia się:**
- Sprawdź console (może być 404 dla endpointu)
- To jest OK! Sekcje gracefully ukrywają się gdy nie ma danych

---

### 🔌 KROK 6: Backend - Implementacja brakujących endpointów

#### Priorytet 1: Podstawowe działanie (już powinno działać)
- ✅ `GET /api/recommendations/lightgcn`
- ✅ `POST /api/interactions`

#### Priorytet 2: Sekcja B (wyjaśnialne rekomendacje)
```python
# backend/routers/recommendations.py

@router.get("/because-borrowed")
async def get_because_borrowed(current_user: User = Depends(get_current_user)):
    """
    Zwraca sekcje "Ponieważ wypożyczyłeś X"
    Dla każdej ostatnio wypożyczonej książki, znajdź podobne
    """
    # 1. Pobierz ostatnie wypożyczenia użytkownika (3-5)
    recent_borrows = await get_user_recent_borrows(current_user.id, limit=3)
    
    sections = []
    for borrowed_book in recent_borrows:
        # 2. Znajdź podobne książki (item-item similarity)
        similar_books = await find_similar_books(
            borrowed_book.id,
            limit=10,
            method="embedding_cosine"  # używa LightGCN embeddings
        )
        
        sections.append({
            "sourceBook": borrowed_book,
            "recommendations": similar_books
        })
    
    return sections

@router.get("/by-genre")
async def get_genre_recommendations(current_user: User = Depends(get_current_user)):
    """
    Top gatunki użytkownika + spersonalizowane książki
    """
    # 1. Znajdź top gatunki użytkownika
    top_genres = await get_user_top_genres(current_user.id, limit=3)
    
    sections = []
    for genre in top_genres:
        # 2. Filtruj książki według gatunku
        genre_books = await get_books_by_genre(genre)
        
        # 3. Rerank używając LightGCN embeddings
        reranked = await personalize_ranking(
            current_user.id,
            genre_books,
            limit=10
        )
        
        sections.append({
            "genre": genre,
            "books": reranked
        })
    
    return sections

# Podobnie dla innych endpointów...
```

#### Priorytet 3: Sekcja C (odkrywanie)
- `GET /api/recommendations/new-arrivals`
- `GET /api/recommendations/librarian-picks`

---

### 🎯 KROK 7: Tymczasowe dane (opcjonalne)

Jeśli backend nie jest jeszcze gotowy, możesz użyć mock data:

```jsx
// W RecommendationsPage.jsx - dodaj na początku pliku

const USE_MOCK_DATA = process.env.NODE_ENV === 'development';

const MOCK_DATA = {
  becauseSections: [
    {
      sourceBook: {
        _id: 'mock1',
        title: 'Harry Potter',
        author: 'J.K. Rowling',
        coverImage: 'https://via.placeholder.com/200x300',
      },
      recommendations: [
        {
          _id: 'mock2',
          title: 'Percy Jackson',
          author: 'Rick Riordan',
          matchScore: 0.88,
          genres: ['Fantasy', 'Adventure'],
          // ... etc
        },
      ],
    },
  ],
  // ... inne mock sections
};

// W fetchAllRecommendations - zamiast API call:
if (USE_MOCK_DATA) {
  setBecauseSections(MOCK_DATA.becauseSections);
  setGenreSections(MOCK_DATA.genreSections);
  // ... etc
} else {
  // Normalne API calls
}
```

---

### 🚀 KROK 8: Wdrożenie produkcyjne

#### 8.1 Sprawdź build
```bash
npm run build
# lub
yarn build
```

Nie powinno być błędów TypeScript/ESLint.

#### 8.2 Test end-to-end
1. Zaloguj się jako użytkownik
2. Wypożycz kilka książek
3. Odwiedź `/recommendations`
4. Sprawdź czy:
   - MMR controls działają
   - Sekcje się ładują
   - Interakcje są trackowane
   - Nawigacja działa

#### 8.3 Monitoring
Dodaj Google Analytics / własny tracking:

```jsx
// W RecommendationsPage.jsx
useEffect(() => {
  // Track page view
  analytics.track('Recommendations Page Viewed', {
    mmrEnabled,
    lambdaValue,
    sectionsLoaded: {
      topRecommendations: topRecommendations.length > 0,
      becauseSections: becauseSections.length > 0,
      // ... etc
    },
  });
}, []);
```

---

## 🔍 Troubleshooting

### Problem: "Cannot find module './components/shared/BookCard'"

**Rozwiązanie:**
```bash
# Sprawdź czy wszystkie pliki zostały skopiowane
ls -la src/pages/recommendations/components/shared/

# Powinno pokazać:
# BookCard.jsx
# SectionTitle.jsx
# HorizontalBookScroll.jsx
# LoadingSkeleton.jsx
```

---

### Problem: "404 Not Found for /api/recommendations/by-genre"

**Rozwiązanie:**
To jest OK! Komponent gracefully ukryje tę sekcję.

Aby naprawić:
1. Zaimplementuj endpoint w backendzie (zobacz KROK 6)
2. Lub użyj mock data (zobacz KROK 7)

---

### Problem: "Recommendations not loading / infinite spinner"

**Debug:**
1. Otwórz DevTools → Network
2. Sprawdź czy API calls są wysyłane
3. Sprawdź response (200 OK? 404? 500?)
4. Sprawdź console errors

**Typowe przyczyny:**
- Backend nie działa
- Błędny token autoryzacji
- CORS error
- Błędny format danych z API

---

### Problem: "MMR controls don't change recommendations"

**Debug:**
```jsx
// W RecommendationsPage.jsx - dodaj logi
useEffect(() => {
  console.log('🔄 MMR settings changed:', { mmrEnabled, lambdaValue, authorLimit });
  fetchAllRecommendations();
}, [mmrEnabled, lambdaValue, authorLimit]);
```

Sprawdź czy:
1. `fetchAllRecommendations()` jest wywoływane
2. Nowe parametry są wysyłane do API
3. Backend faktycznie używa tych parametrów

---

## ✅ Checklist migracji

Przed oznaczeniem jako "gotowe", sprawdź:

### Frontend
- [ ] Wszystkie pliki skopiowane
- [ ] Importy działają
- [ ] Strona się renderuje
- [ ] Console nie ma błędów
- [ ] MMR controls działają
- [ ] Nawigacja działa (kliknięcie książki → szczegóły)
- [ ] Interakcje są trackowane
- [ ] Loading states działają
- [ ] Empty states działają
- [ ] Responsywność (mobile/tablet/desktop)

### Backend (stopniowo)
- [ ] `GET /api/recommendations/lightgcn` (powinien już działać)
- [ ] `POST /api/interactions` (powinien już działać)
- [ ] `GET /api/recommendations/because-borrowed`
- [ ] `GET /api/recommendations/by-genre`
- [ ] `GET /api/recommendations/by-author`
- [ ] `GET /api/recommendations/similar-readers`
- [ ] `GET /api/recommendations/new-arrivals`
- [ ] `GET /api/recommendations/librarian-picks`
- [ ] `GET /api/recommendations/metrics`

### Testing
- [ ] Unit tests dla komponentów
- [ ] Integration tests dla API calls
- [ ] E2E test dla user flow
- [ ] Performance test (load time < 2s)
- [ ] Accessibility test (WCAG AA)

### Documentation
- [ ] README.md przeczytane
- [ ] api-examples.js przeczytane
- [ ] Komentarze w kodzie zaktualizowane
- [ ] Dokumentacja w pracy dyplomowej

---

## 🎓 Dla pracy dyplomowej

W rozdziale praktycznym możesz opisać:

### 3.X Refaktoryzacja architektury frontendu

**Problem:**
Oryginalny kod `RecommendationsPage.jsx` liczył ~1500 linii, co utrudniało:
- Utrzymanie i rozwój
- Testowanie poszczególnych funkcji
- Współpracę w zespole
- Debugowanie błędów

**Rozwiązanie:**
Zastosowano podejście **Component-Based Architecture**:

1. **Separation of Concerns** - każda sekcja w osobnym pliku
2. **DRY Principle** - shared components eliminują duplikację
3. **Single Responsibility** - każdy komponent ma jedną odpowiedzialność
4. **Composition over Inheritance** - małe komponenty składane w większe

**Rezultat:**
- ✅ Główny plik zmniejszony z 1500 do 300 linii (-80%)
- ✅ 9 modularnych komponentów sekcji
- ✅ 4 reużywalne shared components
- ✅ Łatwiejsze testowanie (każdy komponent osobno)
- ✅ Lepsza czytelność i utrzymanie kodu

**Diagram architektury:**
```
[RecommendationsPage (300 LOC)]
        ↓
    ┌───┴───┐
    │ State │ (MMR settings, data)
    └───┬───┘
        ↓
   ┌────┴────┐
   │ Fetch   │ (9 parallel API calls)
   └────┬────┘
        ↓
┌───────┴────────┐
│ Render Sections│
└────────────────┘
   ↓    ↓    ↓
[A]  [B]  [C]
```

---

**Powodzenia w migracji! 🚀**

Jeśli napotkasz problemy:
1. Sprawdź console errors
2. Przeczytaj README.md
3. Zobacz api-examples.js
4. Porównaj z oryginalnym kodem (.OLD.jsx)
