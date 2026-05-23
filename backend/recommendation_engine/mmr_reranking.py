import logging
import math
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

COMICS_MANGA_GENRES = {
    "manga",
    "mangas",
    "comics",
    "graphic novel",
    "graphic novels",
    "comics graphic novels",
    "comics and graphic novels",
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


def _normalize(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("&", " and ")
    value = value.replace("-", " ")
    value = " ".join(value.split())
    aliases = {
        "non fiction": "nonfiction",
        "ya": "young adult",
        "sci fi": "science fiction",
        "sci-fi": "science fiction",
        "scifi": "science fiction",
        "mangas": "manga",
        "graphic novel": "graphic novels",
        "comics graphic novels": "graphic novels",
        "comics and graphic novels": "graphic novels",
    }
    return aliases.get(value, value)


def get_book_authors(book: Dict) -> List[str]:
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


def get_book_genres(book: Dict) -> List[str]:
    genres = _as_list(book.get("canonical_genres"))
    if genres:
        return [_normalize(genre) for genre in genres]

    genres = _as_list(book.get("genres"))
    if not genres:
        genres = _as_list(book.get("genre"))

    return [_normalize(genre) for genre in genres]


def get_book_clusters(book: Dict) -> List[str]:
    clusters = _as_list(book.get("recommendation_clusters"))
    if clusters:
        return clusters

    inferred = []
    seen = set()
    for genre in get_book_genres(book):
        cluster = (
            "comics_manga"
            if genre in COMICS_MANGA_GENRES or "manga" in genre or "comic" in genre
            else genre
        )
        if cluster not in seen:
            seen.add(cluster)
            inferred.append(cluster)
    return inferred


def get_series_key(book: Dict) -> Optional[str]:
    series_key = book.get("series_key")
    if series_key:
        return str(series_key)
    return None


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = dot_product / (norm1 * norm2)
    return (similarity + 1) / 2


def _jaccard_similarity(values1: List[str], values2: List[str]) -> float:
    set1 = set(values1)
    set2 = set(values2)

    if not set1 or not set2:
        return 0.0

    union = set1 | set2
    if not union:
        return 0.0

    return len(set1 & set2) / len(union)


def genre_diversity_score(book1: Dict, book2: Dict) -> float:
    return 1.0 - _jaccard_similarity(get_book_genres(book1), get_book_genres(book2))


def author_diversity_score(book1: Dict, book2: Dict) -> float:
    authors1 = set(get_book_authors(book1))
    authors2 = set(get_book_authors(book2))

    if not authors1 or not authors2:
        return 0.5

    return 0.0 if authors1 & authors2 else 1.0


def cluster_diversity_score(book1: Dict, book2: Dict) -> float:
    return 1.0 - _jaccard_similarity(get_book_clusters(book1), get_book_clusters(book2))


def series_diversity_score(book1: Dict, book2: Dict) -> float:
    series1 = get_series_key(book1)
    series2 = get_series_key(book2)

    if not series1 or not series2:
        return 1.0

    return 0.0 if series1 == series2 else 1.0


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
            weights.append(0.45)

    if use_content_similarity:
        genre_sim = 1.0 - genre_diversity_score(book1, book2)
        similarity_scores.append(genre_sim)
        weights.append(0.25)

        cluster_sim = 1.0 - cluster_diversity_score(book1, book2)
        similarity_scores.append(cluster_sim)
        weights.append(0.25)

        author_sim = 1.0 - author_diversity_score(book1, book2)
        similarity_scores.append(author_sim)
        weights.append(0.20)

        series_sim = 1.0 - series_diversity_score(book1, book2)
        if series_sim > 0:
            similarity_scores.append(series_sim)
            weights.append(0.30)

    if not similarity_scores:
        return 0.5

    total_weight = sum(weights)
    return sum(score * weight for score, weight in zip(similarity_scores, weights)) / total_weight


def _normalize_candidate_scores(candidates: List[Dict]) -> None:
    scores = [float(candidate.get("score", 0.0) or 0.0) for candidate in candidates]
    if not scores:
        return

    min_score = min(scores)
    max_score = max(scores)
    score_range = max_score - min_score

    if score_range > 0:
        for candidate in candidates:
            original_score = float(candidate.get("score", 0.0) or 0.0)
            candidate["normalized_score"] = (original_score - min_score) / score_range
    else:
        for candidate in candidates:
            candidate["normalized_score"] = 1.0


def _primary_author(book: Dict) -> Optional[str]:
    authors = get_book_authors(book)
    return authors[0] if authors else None


def _first_limited_cluster(book: Dict, cluster_limits: Optional[Dict[str, int]]) -> Optional[str]:
    if not cluster_limits:
        return None
    for cluster in get_book_clusters(book):
        if cluster in cluster_limits:
            return cluster
    return None


def _exceeds_limits(
    candidate: Dict,
    author_counts: Dict[str, int],
    series_counts: Dict[str, int],
    cluster_counts: Dict[str, int],
    enforce_author_limit: bool,
    max_per_author: int,
    max_per_series: int,
    cluster_limits: Optional[Dict[str, int]],
) -> bool:
    if enforce_author_limit:
        author = _primary_author(candidate)
        if author and author_counts.get(author, 0) >= max_per_author:
            return True

    series_key = get_series_key(candidate)
    if series_key and max_per_series > 0 and series_counts.get(series_key, 0) >= max_per_series:
        return True

    cluster = _first_limited_cluster(candidate, cluster_limits)
    if cluster and cluster_counts.get(cluster, 0) >= cluster_limits[cluster]:
        return True

    return False


def _record_limits(
    chosen: Dict,
    author_counts: Dict[str, int],
    series_counts: Dict[str, int],
    cluster_counts: Dict[str, int],
) -> None:
    author = _primary_author(chosen)
    if author:
        author_counts[author] = author_counts.get(author, 0) + 1

    series_key = get_series_key(chosen)
    if series_key:
        series_counts[series_key] = series_counts.get(series_key, 0) + 1

    for cluster in get_book_clusters(chosen):
        cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1


def mmr_rerank(
    candidates: List[Dict],
    n: int = 10,
    lambda_param: float = 0.7,
    embeddings_dict: Optional[Dict[str, np.ndarray]] = None,
    use_content_similarity: bool = True,
    enforce_author_limit: bool = True,
    max_per_author: int = 2,
    max_per_series: int = 2,
    cluster_limits: Optional[Dict[str, int]] = None,
) -> List[Dict]:
    if not candidates:
        logger.warning("MMR: no candidates to rerank")
        return []

    if n >= len(candidates):
        logger.info("MMR: requested n >= candidates, returning candidates without rerank")
        return candidates[:n]

    logger.info(
        "MMR reranking: %s candidates -> %s results, lambda=%.2f, author_limit=%s",
        len(candidates),
        n,
        lambda_param,
        max_per_author if enforce_author_limit else "off",
    )

    _normalize_candidate_scores(candidates)

    selected: List[Dict] = []
    remaining = candidates.copy()
    author_counts: Dict[str, int] = {}
    series_counts: Dict[str, int] = {}
    cluster_counts: Dict[str, int] = {}

    while len(selected) < n and remaining:
        best_mmr_score = -np.inf
        best_idx = None

        for idx, candidate in enumerate(remaining):
            if _exceeds_limits(
                candidate,
                author_counts,
                series_counts,
                cluster_counts,
                enforce_author_limit,
                max_per_author,
                max_per_series,
                cluster_limits,
            ):
                continue

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

            if mmr_score > best_mmr_score:
                best_mmr_score = mmr_score
                best_idx = idx

        if best_idx is None:
            # The hard limits did their job; relax them only to fill the page.
            logger.info("MMR: relaxing diversity limits to fill remaining slots")
            for idx, candidate in enumerate(remaining):
                relevance = candidate.get("normalized_score", 0.5)
                max_similarity = (
                    max(
                        calculate_similarity(
                            candidate,
                            selected_book,
                            embeddings_dict=embeddings_dict,
                            use_content_similarity=use_content_similarity,
                        )
                        for selected_book in selected
                    )
                    if selected
                    else 0.0
                )
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_idx = idx

        if best_idx is None:
            break

        chosen = remaining.pop(best_idx)
        selected.append(chosen)
        _record_limits(chosen, author_counts, series_counts, cluster_counts)

    for i, book in enumerate(selected):
        book["mmr_rank"] = i + 1
        book["diversified"] = True

    logger.info(
        "MMR complete: %s books, %s authors, clusters=%s",
        len(selected),
        len(author_counts),
        dict(cluster_counts),
    )

    return selected


def apply_mmr_with_offset(
    candidates: List[Dict], n: int = 10, offset: int = 0, lambda_param: float = 0.7, **mmr_kwargs
) -> Tuple[List[Dict], int]:
    fetch_n = min(n * 3 + offset, len(candidates))
    diversified = mmr_rerank(candidates, n=fetch_n, lambda_param=lambda_param, **mmr_kwargs)
    result = diversified[offset : offset + n]
    next_offset = offset + n
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

        logger.info("Extracted %s book embeddings", len(embeddings_dict))
    except Exception as e:
        logger.error("Failed to extract embeddings: %s", e)

    return embeddings_dict


def _entropy(counts: Counter) -> float:
    if not counts:
        return 0.0
    total = sum(counts.values())
    probs = [count / total for count in counts.values()]
    return -sum(prob * math.log2(prob) for prob in probs if prob > 0)


def diversity_metrics(books: List[Dict]) -> Dict[str, float]:
    all_genres = []
    all_authors = []
    all_clusters = []
    all_series = []

    for book in books:
        all_genres.extend(get_book_genres(book))
        all_authors.extend(get_book_authors(book))
        all_clusters.extend(get_book_clusters(book))
        series_key = get_series_key(book)
        if series_key:
            all_series.append(series_key)

    genre_counts = Counter(all_genres)
    author_counts = Counter(all_authors)
    cluster_counts = Counter(all_clusters)
    series_counts = Counter(all_series)

    pairwise_diffs = []
    for i in range(len(books)):
        for j in range(i + 1, len(books)):
            genre_diff = genre_diversity_score(books[i], books[j])
            author_diff = author_diversity_score(books[i], books[j])
            cluster_diff = cluster_diversity_score(books[i], books[j])
            series_diff = series_diversity_score(books[i], books[j])
            avg_diff = (genre_diff + author_diff + cluster_diff + series_diff) / 4
            pairwise_diffs.append(avg_diff)

    return {
        "unique_genres": len(genre_counts),
        "unique_authors": len(author_counts),
        "unique_clusters": len(cluster_counts),
        "unique_series": len(series_counts),
        "genre_entropy": _entropy(genre_counts),
        "author_entropy": _entropy(author_counts),
        "cluster_entropy": _entropy(cluster_counts),
        "avg_pairwise_dissimilarity": float(np.mean(pairwise_diffs)) if pairwise_diffs else 0.0,
        "num_books": len(books),
        "cluster_counts": dict(cluster_counts),
    }
