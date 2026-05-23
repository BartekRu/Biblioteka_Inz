import re
from typing import Iterable, List


GENRE_ALIASES = {
    "non fiction": "nonfiction",
    "non-fiction": "nonfiction",
    "ya": "young adult",
    "sci fi": "science fiction",
    "sci-fi": "science fiction",
    "scifi": "science fiction",
    "graphic novel": "graphic novels",
    "graphic novels": "graphic novels",
    "comics graphic novels": "graphic novels",
    "comics and graphic novels": "graphic novels",
    "mangas": "manga",
}

COMICS_MANGA_GENRES = {
    "manga",
    "comics",
    "graphic novels",
}


def _as_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return [str(value).strip()] if str(value).strip() else []


def normalize_genre(genre: str) -> str:
    if not genre:
        return ""

    normalized = genre.strip().lower()
    normalized = normalized.replace("&", " and ")
    normalized = normalized.replace("-", " ")
    normalized = " ".join(normalized.split())
    return GENRE_ALIASES.get(normalized, normalized)


def get_genres(book: dict) -> List[str]:
    genres = _as_list(book.get("genres"))
    if not genres:
        genres = _as_list(book.get("genre"))
    return genres


def get_authors(book: dict) -> List[str]:
    authors = _as_list(book.get("authors"))
    if authors:
        return authors

    author = _as_list(book.get("author"))
    if author:
        return author

    authors_full = book.get("authors_full")
    if isinstance(authors_full, str):
        return [item.strip() for item in authors_full.split(",") if item.strip()]

    return []


def canonicalize_genres(genres: Iterable[str]) -> List[str]:
    seen = set()
    canonical = []
    for genre in genres:
        normalized = normalize_genre(genre)
        if normalized and normalized not in seen:
            seen.add(normalized)
            canonical.append(normalized)
    return canonical


def recommendation_clusters_for_genres(genres: Iterable[str]) -> List[str]:
    canonical = canonicalize_genres(genres)
    clusters = []
    seen = set()

    for genre in canonical:
        if genre in COMICS_MANGA_GENRES or "manga" in genre or "comic" in genre:
            cluster = "comics_manga"
        else:
            cluster = genre

        if cluster not in seen:
            seen.add(cluster)
            clusters.append(cluster)

    return clusters


def infer_series_key(title: str) -> str | None:
    if not title:
        return None

    value = title.strip().lower()

    match = re.search(r"\(([^)]*#\s*\d+[^)]*)\)", value)
    if match:
        candidate = re.split(r"[,#]", match.group(1), maxsplit=1)[0].strip()
        if len(candidate) >= 3:
            return _clean_series_key(candidate)

    value = re.sub(r"\([^)]*\)", "", value)
    value = re.sub(r"\b(vol\.?|volume|book|tom|part)\s*\d+\b.*$", "", value)
    value = re.sub(r"\b#\s*\d+\b.*$", "", value)
    value = value.split(":")[0]
    value = value.split(",")[0]
    return _clean_series_key(value)


def _clean_series_key(value: str) -> str | None:
    cleaned = re.sub(r"[^a-z0-9]+", " ", value.lower())
    cleaned = " ".join(cleaned.split())
    if len(cleaned) < 3:
        return None
    return cleaned


def enrich_book_contract(book: dict) -> dict:
    if not book:
        return book

    genres = get_genres(book)
    authors = get_authors(book)

    book["genres"] = genres
    book["authors"] = authors
    book["canonical_genres"] = canonicalize_genres(genres)
    book["recommendation_clusters"] = recommendation_clusters_for_genres(genres)
    book["series_key"] = book.get("series_key") or infer_series_key(book.get("title", ""))

    if authors and not book.get("author"):
        book["author"] = authors[0]

    return book
