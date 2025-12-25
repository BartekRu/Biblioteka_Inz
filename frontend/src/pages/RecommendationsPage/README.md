# 📚 RecommendationsPage - Refactoring Documentation

## 🎯 Cel refaktoringu

Oryginalny plik `RecommendationsPage.jsx` miał ~1500 linii i był trudny w utrzymaniu. Zrefaktoryzowany kod został podzielony na **mniejsze, modularne komponenty** zgodnie z nową strukturą sekcji.

---

## 📂 Struktura plików

```
recommendations/
├── RecommendationsPage.jsx          # 🎭 Główny orkiestrator (~300 linii)
├── components/
│   ├── shared/                      # 🔧 Komponenty współdzielone
│   │   ├── BookCard.jsx            # Karta pojedynczej książki
│   │   ├── SectionTitle.jsx        # Tytuł sekcji z ikoną
│   │   ├── HorizontalBookScroll.jsx # Poziome przewijanie książek
│   │   └── LoadingSkeleton.jsx     # Szkielety ładowania
│   ├── controls/                    # ⚙️ Kontrolki
│   │   └── MMRControlPanel.jsx     # Panel sterowania MMR
│   ├── sectionA/                    # 🎯 Sekcja A: Główne rekomendacje
│   │   └── TopRecommendations.jsx  # LightGCN + MMR
│   ├── sectionB/                    # 🧠 Sekcja B: Rekomendacje wyjaśnialne
│   │   ├── BecauseYouBorrowed.jsx  # "Ponieważ wypożyczyłeś..."
│   │   ├── GenreRecommendations.jsx # "Dla miłośników gatunku..."
│   │   ├── AuthorBooks.jsx          # "Inne dzieła autora..."
│   │   └── SimilarReaders.jsx       # "Popularne wśród podobnych..."
│   └── sectionC/                    # 🔍 Sekcja C: Odkrywanie
│       ├── DiverseDiscovery.jsx     # "Odkryj coś nowego"
│       ├── NewArrivals.jsx          # "Nowości w bibliotece"
│       └── LibrarianPicks.jsx       # "Polecane przez bibliotekarzy"
├── styles/
│   └── theme.js                     # 🎨 Kolory i style Steam-inspired
└── utils/
    └── bookHelpers.js               # 🛠️ Funkcje pomocnicze
```

---

## 🏗️ Architektura komponentów

### 1️⃣ **Shared Components** (Komponenty współdzielone)

#### `BookCard.jsx`
- **Cel**: Wyświetlanie pojedynczej książki
- **Props**:
  - `book` - dane książki
  - `onClick` - callback przy kliknięciu
  - `showScore` - czy pokazywać match score
  - `showReason` - czy pokazywać powód rekomendacji
  - `compact` - tryb kompaktowy
  - `interactionSource` - źródło interakcji (do śledzenia)

```jsx
<BookCard
  book={book}
  onClick={() => navigate(`/books/${book._id}`)}
  showScore={true}
  showReason={true}
  interactionSource="top-recommendations"
/>
```

#### `HorizontalBookScroll.jsx`
- **Cel**: Poziome przewijanie listy książek z przyciskami nawigacji
- **Props**:
  - `books` - tablica książek
  - `onBookClick` - callback przy kliknięciu książki
  - Pozostałe dziedziczone z `BookCard`

```jsx
<HorizontalBookScroll
  books={topBooks}
  onBookClick={handleBookClick}
  showScore={true}
  interactionSource="genre-recs"
/>
```

#### `SectionTitle.jsx`
- **Cel**: Spójny tytuł sekcji z ikoną i opcjonalnym przyciskiem akcji
- **Props**:
  - `icon` - komponent ikony MUI
  - `title` - tekst tytułu
  - `subtitle` - opcjonalny podtytuł
  - `actionLabel` - tekst przycisku
  - `onAction` - callback przycisku

```jsx
<SectionTitle
  icon={AutoAwesome}
  title="Dla Ciebie"
  subtitle="Spersonalizowane rekomendacje"
  actionLabel="Zobacz wszystkie"
  onAction={() => navigate('/all')}
/>
```

#### `LoadingSkeleton.jsx`
- **Cel**: Szkielety ładowania dla różnych typów sekcji
- **Eksporty**:
  - `BookCardSkeleton`
  - `HorizontalScrollSkeleton`
  - `SectionTitleSkeleton`
  - `SectionSkeleton`

---

### 2️⃣ **Section Components** (Komponenty sekcji)

Każda sekcja ma podobną strukturę:

```jsx
const SectionComponent = ({ data, loading }) => {
  // 1. Handler nawigacji
  const handleBookClick = async (book) => {
    await recommendationsAPI.reportInteraction(...);
    navigate(`/books/${book._id}`);
  };

  // 2. Loading state
  if (loading) return <LoadingSkeleton.Section />;

  // 3. Empty state
  if (!data || data.length === 0) return null;

  // 4. Render
  return (
    <Box sx={pageStyles.sectionContainer}>
      <SectionTitle ... />
      <HorizontalBookScroll ... />
      <ExplanationPaper ... />
    </Box>
  );
};
```

---

## 🔄 Data Flow

### Główny komponent `RecommendationsPage.jsx`

```jsx
// 1. State Management
const [topRecommendations, setTopRecommendations] = useState([]);
const [becauseSections, setBecauseSections] = useState([]);
// ... etc

// 2. Fetch wszystkich sekcji równolegle
const fetchAllRecommendations = async () => {
  const [topRes, becauseRes, ...] = await Promise.allSettled([
    recommendationsAPI.getUserLightGCN(...),
    recommendationsAPI.getBecauseYouBorrowed(),
    // ... etc
  ]);

  // Process results
  setTopRecommendations(topRes.value.data);
  // ... etc
};

// 3. Render sekcji
return (
  <Container>
    <MMRControlPanel ... />
    
    {/* SEKCJA A */}
    <TopRecommendations books={topRecommendations} />
    
    {/* SEKCJA B */}
    <BecauseYouBorrowed sections={becauseSections} />
    <GenreRecommendations genreSections={genreSections} />
    // ... etc
  </Container>
);
```

---

## 🎨 Style System

### `theme.js`

Centralne miejsce dla wszystkich kolorów i stylów:

```jsx
import { COLORS, pageStyles, animations } from './styles/theme';

// Użycie
<Box sx={{ color: COLORS.accent }}>...</Box>
<Typography sx={pageStyles.sectionTitle}>...</Typography>
<Card sx={{ ...animations.cardHover }}>...</Card>
```

---

## 🛠️ Utils

### `bookHelpers.js`

Funkcje pomocnicze do przetwarzania danych książek:

```jsx
import {
  getBookImage,
  getBookGenres,
  getBookRating,
  isBookAvailable,
  getMatchScorePercent,
  truncateText,
} from './utils/bookHelpers';

// Użycie
const coverUrl = getBookImage(book);
const genres = getBookGenres(book);
const rating = getBookRating(book);
```

---

## 🔌 API Integration

Każda sekcja reportuje interakcje do analytics:

```jsx
await recommendationsAPI.reportInteraction(
  bookId,
  'view',
  {
    source: 'section-name',
    mmr_enabled: true,
    // ... dodatkowe metadata
  }
);
```

---

## 📊 Sekcje rekomendacji

### SEKCJA A: Główne rekomendacje
- **TopRecommendations** - 6-8 najlepszych z LightGCN + MMR
- Pokazuje wyjaśnienie działania algorytmu
- Metryki różnorodności

### SEKCJA B: Rekomendacje wyjaśnialne
1. **BecauseYouBorrowed** - podobne książki (item-item CF)
2. **GenreRecommendations** - filtrowane przez gatunek + personalizacja
3. **AuthorBooks** - inne dzieła autora + ranking
4. **SimilarReaders** - user-based CF

### SEKCJA C: Odkrywanie
1. **DiverseDiscovery** - MMR z λ=0.3 (wysoka różnorodność)
2. **NewArrivals** - cold-start handling
3. **LibrarianPicks** - hybrydowe (kuratorskie + AI)

---

## 🚀 Migracja z oryginalnego kodu

### Krok 1: Kopiuj pliki
```bash
cp -r recommendations-refactor/* src/pages/recommendations/
```

### Krok 2: Zaktualizuj importy w `App.jsx` lub routing
```jsx
import RecommendationsPage from './pages/recommendations/RecommendationsPage';
```

### Krok 3: Zaktualizuj API endpoints (jeśli potrzeba)

Nowe endpointy:
- `recommendationsAPI.getGenreRecommendations()`
- `recommendationsAPI.getAuthorRecommendations()`
- `recommendationsAPI.getSimilarReadersBooks()`
- `recommendationsAPI.getNewArrivals()`
- `recommendationsAPI.getLibrarianPicks()`

---

## 🧪 Testing

Każdy komponent można testować osobno:

```jsx
import { render } from '@testing-library/react';
import BookCard from './components/shared/BookCard';

test('renders book card', () => {
  const book = { _id: '1', title: 'Test', author: 'Author' };
  render(<BookCard book={book} onClick={() => {}} />);
});
```

---

## 📈 Korzyści refaktoringu

✅ **Modularność** - każda sekcja w osobnym pliku
✅ **Reużywalność** - shared components używane wszędzie
✅ **Czytelność** - główny plik ~300 linii zamiast 1500
✅ **Utrzymanie** - łatwiej znaleźć i naprawić błędy
✅ **Testowanie** - komponenty można testować osobno
✅ **Skalowanie** - łatwo dodawać nowe sekcje

---

## 🔧 Rozszerzanie systemu

### Dodawanie nowej sekcji:

1. Stwórz nowy komponent w odpowiednim folderze:
```jsx
// components/sectionX/NewSection.jsx
const NewSection = ({ data, loading }) => {
  // ... implementation
};
export default NewSection;
```

2. Dodaj endpoint w API (jeśli potrzeba)

3. Zintegruj w `RecommendationsPage.jsx`:
```jsx
const [newSectionData, setNewSectionData] = useState([]);

// W fetchAllRecommendations:
const newSectionRes = await recommendationsAPI.getNewSection();
setNewSectionData(newSectionRes.value.data);

// W render:
<NewSection data={newSectionData} loading={loading} />
```

---

## 📝 Checklist implementacji backendu

Backend powinien wspierać następujące endpointy:

- [x] `GET /api/recommendations/lightgcn` - główne rekomendacje
- [ ] `GET /api/recommendations/because-borrowed` - podobne do wypożyczonych
- [ ] `GET /api/recommendations/by-genre` - według gatunku
- [ ] `GET /api/recommendations/by-author` - według autora
- [ ] `GET /api/recommendations/similar-readers` - od podobnych użytkowników
- [ ] `GET /api/recommendations/new-arrivals` - nowości
- [ ] `GET /api/recommendations/librarian-picks` - wybór bibliotekarzy
- [x] `POST /api/interactions` - śledzenie interakcji

---

## 🎓 Dla celów inżynierskich

Ten refaktoring doskonale pokazuje:

1. **Separation of Concerns** - każda sekcja ma swoją odpowiedzialność
2. **DRY Principle** - shared components eliminują duplikację
3. **Component Composition** - małe komponenty składane w większe
4. **Single Responsibility** - każdy komponent robi jedną rzecz dobrze
5. **Explainability** - każda sekcja wyjaśnia działanie algorytmu

Idealne do opisania w pracy dyplomowej! 📖

---

## 🤝 Współpraca z backendem

Format danych API (przykład):

```json
{
  "recommendations": [
    {
      "_id": "book_id",
      "title": "Tytuł",
      "author": "Autor",
      "matchScore": 0.95,
      "recommendationReason": "Podobne do Twojego profilu",
      "genres": ["Fantasy", "Adventure"],
      "averageRating": 4.5,
      "reviewCount": 123,
      "available": true
    }
  ],
  "metadata": {
    "diversity_metrics": {
      "unique_genres": 8,
      "unique_authors": 15,
      "avg_pairwise_dissimilarity": 0.67
    }
  }
}
```

---

**Autor refaktoringu**: Tomasz (Biblioteka_Inz)  
**Data**: 2025-01-25  
**Wersja**: 2.0 (zrefaktoryzowana)
