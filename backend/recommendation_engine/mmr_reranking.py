import numpy as np
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:

    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = dot_product / (norm1 * norm2)
    return (similarity + 1) / 2


def genre_diversity_score(book1: Dict, book2: Dict) -> float:

    genres1 = set(book1.get("genre", []) or [])
    genres2 = set(book2.get("genre", []) or [])

    if not genres1 or not genres2:
        return 0.5

    intersection = len(genres1 & genres2)
    union = len(genres1 | genres2)

    if union == 0:
        return 0.5

    jaccard = intersection / union
    return 1.0 - jaccard


def author_diversity_score(book1: Dict, book2: Dict) -> float:

    authors1 = set(book1.get("authors", []) or [])
    authors2 = set(book2.get("authors", []) or [])

    if not authors1 or not authors2:
        return 0.5

    if authors1 & authors2:
        return 0.0

    return 1.0


def calculate_similarity(
    book1: Dict,
    book2: Dict,
    embeddings_dict: Optional[Dict[str, np.ndarray]] = None,
    use_content_similarity: bool = True,
) -> float:

    similarity_scores = []
    weights = []

    if embeddings_dict:
        book1_id = str(book1.get("_id"))
        book2_id = str(book2.get("_id"))

        if book1_id in embeddings_dict and book2_id in embeddings_dict:
            emb_sim = cosine_similarity(embeddings_dict[book1_id], embeddings_dict[book2_id])
            similarity_scores.append(emb_sim)
            weights.append(0.6)

    if use_content_similarity:
        genre_sim = 1.0 - genre_diversity_score(book1, book2)
        similarity_scores.append(genre_sim)
        weights.append(0.25)

        author_sim = 1.0 - author_diversity_score(book1, book2)
        similarity_scores.append(author_sim)
        weights.append(0.15)

    if not similarity_scores:
        return 0.5

    total_weight = sum(weights)
    weighted_sim = sum(s * w for s, w in zip(similarity_scores, weights)) / total_weight

    return weighted_sim


def mmr_rerank(
    candidates: List[Dict],
    n: int = 10,
    lambda_param: float = 0.7,
    embeddings_dict: Optional[Dict[str, np.ndarray]] = None,
    use_content_similarity: bool = True,
    enforce_author_limit: bool = True,
    max_per_author: int = 2,
) -> List[Dict]:

    if not candidates:
        logger.warning("❌ MMR: brak kandydatów do re-rankingu")
        return []

    if n >= len(candidates):
        logger.info(f"ℹ️ MMR: n={n} >= liczba kandydatów ({len(candidates)}), zwracam wszystko")
        return candidates[:n]

    logger.info(
        f"🔄 MMR re-ranking: {len(candidates)} kandydatów → {n} wyników, "
        f"λ={lambda_param:.2f}, author_limit={max_per_author if enforce_author_limit else 'off'}"
    )

    scores = [c.get("score", 0.0) for c in candidates]
    if scores:
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score

        if score_range > 0:
            for candidate in candidates:
                original_score = candidate.get("score", 0.0)
                normalized = (original_score - min_score) / score_range
                candidate["normalized_score"] = normalized
        else:
            for candidate in candidates:
                candidate["normalized_score"] = 1.0

    selected: List[Dict] = []
    remaining = candidates.copy()
    author_counts: Dict[str, int] = {}

    iteration = 0
    while len(selected) < n and remaining:
        iteration += 1
        best_mmr_score = -np.inf
        best_idx = None

        for idx, candidate in enumerate(remaining):
            relevance = candidate.get("normalized_score", 0.5)

            if not selected:
                max_similarity = 0.0
            else:
                similarities = [
                    calculate_similarity(
                        candidate,
                        selected_book,
                        embeddings_dict=embeddings_dict,
                        use_content_similarity=use_content_similarity,
                    )
                    for selected_book in selected
                ]
                max_similarity = max(similarities) if similarities else 0.0

            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity

            if enforce_author_limit:
                authors = candidate.get("authors", []) or []
                if authors:
                    author = authors[0]
                    current_count = author_counts.get(author, 0)

                    if current_count >= max_per_author:
                        mmr_score *= 0.3

            if mmr_score > best_mmr_score:
                best_mmr_score = mmr_score
                best_idx = idx

        if best_idx is None:
            logger.warning(f"⚠️ MMR: nie znaleziono kandydata w iteracji {iteration}")
            break

        chosen = remaining.pop(best_idx)
        selected.append(chosen)

        if enforce_author_limit:
            authors = chosen.get("authors", []) or []
            if authors:
                author = authors[0]
                author_counts[author] = author_counts.get(author, 0) + 1

        if iteration == 1:
            logger.debug(
                f"  🥇 Pierwszy wybór: {chosen.get('title', 'N/A')} "
                f"(MMR={best_mmr_score:.3f}, relevance={chosen.get('normalized_score', 0):.3f})"
            )

    for i, book in enumerate(selected):
        book["mmr_rank"] = i + 1
        book["diversified"] = True

    logger.info(
        f"✅ MMR zakończone: wybrano {len(selected)} książek, "
        f"{len(set(a for b in selected for a in (b.get('authors', []) or [])))} unikalnych autorów"
    )

    return selected


def apply_mmr_with_offset(
    candidates: List[Dict], n: int = 10, offset: int = 0, lambda_param: float = 0.7, **mmr_kwargs
) -> Tuple[List[Dict], int]:

    fetch_n = min(n * 3 + offset, len(candidates))

    logger.info(f"📊 MMR offset: generuję {fetch_n} wyników, offset={offset}, zwracam {n}")

    diversified = mmr_rerank(candidates, n=fetch_n, lambda_param=lambda_param, **mmr_kwargs)

    result = diversified[offset : offset + n]
    next_offset = offset + n

    logger.info(f"✅ Zwracam {len(result)} książek, next_offset={next_offset}")

    return result, next_offset


def extract_book_embeddings_from_model(model, book_ids: List[str]) -> Dict[str, np.ndarray]:

    embeddings_dict = {}

    try:
        if hasattr(model, "book_id_map"):
            for book_id in book_ids:
                if book_id in model.book_id_map:
                    internal_id = model.book_id_map[book_id]
                    embedding = model.book_embeddings[internal_id].detach().cpu().numpy()
                    embeddings_dict[book_id] = embedding

        logger.info(f"📦 Wyciągnięto {len(embeddings_dict)} embeddingów książek")

    except Exception as e:
        logger.error(f"❌ Błąd przy wyciąganiu embeddingów: {e}")

    return embeddings_dict


def diversity_metrics(books: List[Dict]) -> Dict[str, float]:

    from collections import Counter

    all_genres = []
    all_authors = []

    for book in books:
        all_genres.extend(book.get("genre", []) or [])
        all_authors.extend(book.get("authors", []) or [])

    genre_counts = Counter(all_genres)
    author_counts = Counter(all_authors)

    def calculate_entropy(counts):
        if not counts:
            return 0.0
        total = sum(counts.values())
        probs = [c / total for c in counts.values()]
        return -sum(p * np.log2(p) for p in probs if p > 0)

    pairwise_diffs = []
    for i in range(len(books)):
        for j in range(i + 1, len(books)):
            genre_diff = genre_diversity_score(books[i], books[j])
            author_diff = author_diversity_score(books[i], books[j])
            avg_diff = (genre_diff + author_diff) / 2
            pairwise_diffs.append(avg_diff)

    return {
        "unique_genres": len(genre_counts),
        "unique_authors": len(author_counts),
        "genre_entropy": calculate_entropy(genre_counts),
        "author_entropy": calculate_entropy(author_counts),
        "avg_pairwise_dissimilarity": np.mean(pairwise_diffs) if pairwise_diffs else 0.0,
        "num_books": len(books),
    }


if __name__ == "__main__":
    sample_candidates = [
        {
            "_id": "1",
            "title": "Harry Potter",
            "authors": ["J.K. Rowling"],
            "genre": ["Fantasy", "Young Adult"],
            "score": 0.95,
        },
        {
            "_id": "2",
            "title": "Fantastic Beasts",
            "authors": ["J.K. Rowling"],
            "genre": ["Fantasy"],
            "score": 0.90,
        },
        {
            "_id": "3",
            "title": "The Hobbit",
            "authors": ["J.R.R. Tolkien"],
            "genre": ["Fantasy", "Adventure"],
            "score": 0.88,
        },
        {
            "_id": "4",
            "title": "1984",
            "authors": ["George Orwell"],
            "genre": ["Dystopian", "Science Fiction"],
            "score": 0.85,
        },
        {
            "_id": "5",
            "title": "Animal Farm",
            "authors": ["George Orwell"],
            "genre": ["Dystopian", "Political"],
            "score": 0.82,
        },
    ]

    print("\n" + "=" * 80)
    print("TEST 1: Bez MMR (tylko score z LightGCN)")
    print("=" * 80)
    top_5_no_mmr = sample_candidates[:5]
    for i, book in enumerate(top_5_no_mmr, 1):
        print(f"{i}. {book['title']} by {book['authors'][0]} (score: {book['score']})")

    print("\n" + "=" * 80)
    print("TEST 2: Z MMR (λ=0.7, limit autorów=1)")
    print("=" * 80)
    top_5_with_mmr = mmr_rerank(
        sample_candidates, n=5, lambda_param=0.7, enforce_author_limit=True, max_per_author=1
    )
    for i, book in enumerate(top_5_with_mmr, 1):
        print(f"{i}. {book['title']} by {book['authors'][0]} (score: {book['score']})")

    print("\n" + "=" * 80)
    print("METRYKI RÓŻNORODNOŚCI")
    print("=" * 80)
    metrics_no_mmr = diversity_metrics(top_5_no_mmr)
    metrics_with_mmr = diversity_metrics(top_5_with_mmr)

    print("\nBEZ MMR:")
    for key, value in metrics_no_mmr.items():
        print(f"  {key}: {value:.3f}")

    print("\nZ MMR:")
    for key, value in metrics_with_mmr.items():
        print(f"  {key}: {value:.3f}")
