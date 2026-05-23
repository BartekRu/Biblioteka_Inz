from typing import List, Dict, Optional
from datetime import datetime
from bson import ObjectId
import logging
import numpy as np
from collections import Counter
from ..utils.book_contract import (
    enrich_book_contract,
    get_authors,
    get_genres,
    normalize_genre as contract_normalize_genre,
)
import math  # ✅ FIX #2: Dodano dla eksponencjalnego score

logger = logging.getLogger(__name__)


# ============================================================
# ✅ FIX #3: NORMALIZACJA GATUNKÓW
# ============================================================
GENRE_ALIASES = {
    "non fiction": "nonfiction",
    "ya": "young adult",
    "sci fi": "science fiction",
    "sci-fi": "science fiction",
    "scifi": "science fiction",
}


def normalize_genre(genre: str) -> str:
    """
    Normalizuje nazwy gatunków dla spójnego matchingu.

    "Non Fiction" → "nonfiction"
    "Sci-Fi" → "science fiction"
    "Ya" → "young adult"
    """
    return contract_normalize_genre(genre)


class RecommendationService:

    def __init__(
        self,
        lightgcn_service,
        lightgcn_adapter,
        db,
    ):
        self.lightgcn = lightgcn_service
        self.adapter = lightgcn_adapter
        self.db = db

        self.is_loaded = (
            hasattr(lightgcn_service, "user_emb") and lightgcn_service.user_emb is not None
        )

        # 🆕 Cache dla genre coverage stats
        self._genre_coverage_cache = None
        self._coverage_cache_timestamp = None

        if not self.is_loaded:
            logger.warning(
                "⚠️  GoodbooksLightGCNService not fully loaded - recommendations may fail"
            )
        else:
            num_users = getattr(
                lightgcn_service, "num_users", getattr(lightgcn_service, "n_users", 0)
            )
            num_items = getattr(
                lightgcn_service, "num_items", getattr(lightgcn_service, "n_items", 0)
            )
            logger.info(
                f"✅ RecommendationService initialized with {num_users:,} users and {num_items:,} items"
            )

    async def get_recommendations(
        self, user_id: str, n: int = 30, exclude_books: Optional[List[str]] = None
    ) -> List[Dict]:

        if not self.is_loaded:
            raise RuntimeError("Model not loaded - cannot generate recommendations")

        try:
            exclude_goodbooks_ids = set()
            if exclude_books:
                for mongo_id in exclude_books:
                    goodbooks_id = await self.adapter._get_goodbooks_id(mongo_id)
                    if goodbooks_id:
                        exclude_goodbooks_ids.add(goodbooks_id)

            logger.info(
                f"📊 Excluding {len(exclude_goodbooks_ids)} books for user {user_id[:12]}..."
            )

            try:
                rec_goodbooks_ids = self.lightgcn.get_recommendations_for_user(
                    mongo_user_id=user_id,
                    n=n,
                    exclude_goodbooks_ids=exclude_goodbooks_ids,
                    use_cache=False,
                )
            except Exception as e:
                logger.warning(f"⚠️  get_recommendations_for_user failed: {e}, trying fallback")

                rec_goodbooks_ids = self.lightgcn.recommend_for_goodbooks_ids(
                    list(exclude_goodbooks_ids) if exclude_goodbooks_ids else [], top_k=n
                )

            recommendations = []

            # ============================================================
            # ✅ FIX #2: EKSPONENCJALNY SCORE ZAMIAST LINIOWEGO
            # ============================================================
            for goodbooks_id in rec_goodbooks_ids:
                mongo_book_id = await self.adapter.get_mongo_book_id(goodbooks_id)

                if mongo_book_id:
                    rank = len(recommendations) + 1  # 1-indexed

                    # ✅ NOWY: Eksponencjalny score
                    tau = max(10, n / 10)  # Decay constant (15 dla n=150)
                    exponential_score = math.exp(-rank / tau)

                    # ❌ STARY (liniowy): score = 1.0 - (len(recommendations) / n)

                    recommendations.append(
                        {
                            "book_id": mongo_book_id,
                            "goodbooks_id": goodbooks_id,
                            "score": exponential_score,  # ✅ Eksponencjalny!
                        }
                    )

            logger.info(
                f"✅ Generated {len(recommendations)} recommendations for user {user_id[:12]}..."
            )

            return recommendations

        except Exception as e:
            logger.error(
                f"❌ Failed to generate recommendations for user {user_id}: {e}", exc_info=True
            )
            raise

    # ============================================================
    #   ✅ FIX #3: Genre coverage stats Z NORMALIZACJĄ
    # ============================================================

    async def _get_genre_coverage_stats(self, force_refresh: bool = False) -> Dict[str, float]:
        """
        Oblicza coverage każdego gatunku w bazie danych.

        ✅ NOWE: Normalizuje gatunki przed zliczaniem!

        Coverage = (liczba książek z gatunkiem) / (wszystkie książki)

        Returns:
            Dict[normalized_genre, coverage_percentage]
            np. {"nonfiction": 0.514, "business": 0.020, "poetry": 0.005}

        Cache'uje wynik żeby nie liczyć za każdym razem.
        Cache odświeża się co 1 godzinę lub na force_refresh=True.
        """
        from datetime import timedelta

        # Sprawdź cache
        now = datetime.utcnow()
        cache_valid = (
            self._genre_coverage_cache is not None
            and self._coverage_cache_timestamp is not None
            and (now - self._coverage_cache_timestamp) < timedelta(hours=1)
        )

        if cache_valid and not force_refresh:
            logger.debug(
                f"📊 Using cached genre coverage ({len(self._genre_coverage_cache)} genres)"
            )
            return self._genre_coverage_cache

        logger.info("🔄 Computing genre coverage stats from database...")

        try:
            # Zlicz wszystkie książki
            total_books = await self.db.books.count_documents({})

            if total_books == 0:
                logger.warning("No books in database!")
                return {}

            # Agregacja: rozwiń gatunki i zlicz
            pipeline = [
                # Normalizuj pole genre/genres do jednej listy
                {
                    "$addFields": {
                        "normalized_genres": {
                            "$cond": [
                                {"$isArray": "$genre"},
                                "$genre",
                                {
                                    "$cond": [
                                        {"$isArray": "$genres"},
                                        "$genres",
                                        {
                                            "$cond": [
                                                {"$ne": ["$genre", None]},
                                                ["$genre"],
                                                {
                                                    "$cond": [
                                                        {"$ne": ["$genres", None]},
                                                        ["$genres"],
                                                        [],
                                                    ]
                                                },
                                            ]
                                        },
                                    ]
                                },
                            ]
                        }
                    }
                },
                # Rozwiń listę gatunków
                {"$unwind": "$normalized_genres"},
                # Grupuj i licz
                {"$group": {"_id": "$normalized_genres", "count": {"$sum": 1}}},
                # Sortuj po count DESC
                {"$sort": {"count": -1}},
            ]

            # ✅ NOWE: Normalizuj gatunki przy zliczaniu
            raw_coverage = {}

            async for doc in self.db.books.aggregate(pipeline):
                genre = doc["_id"]
                count = doc["count"]

                if genre:  # Skip empty/null genres
                    raw_coverage[genre] = count

            # ✅ Normalizuj nazwy gatunków
            coverage_stats = {}
            for raw_genre, count in raw_coverage.items():
                norm_genre = normalize_genre(raw_genre)

                # Agreguj duplikaty (np. "Non Fiction" + "Nonfiction" → "nonfiction")
                if norm_genre in coverage_stats:
                    coverage_stats[norm_genre] += count
                else:
                    coverage_stats[norm_genre] = count

            # Przelicz na coverage percentage
            for genre in coverage_stats:
                coverage_stats[genre] = coverage_stats[genre] / total_books

            # Cache wyniki
            self._genre_coverage_cache = coverage_stats
            self._coverage_cache_timestamp = now

            logger.info(
                f"✅ Genre coverage computed: {len(coverage_stats)} genres, "
                f"total_books={total_books:,}"
            )

            # Log top 10 i bottom 10
            sorted_genres = sorted(coverage_stats.items(), key=lambda x: x[1], reverse=True)
            logger.info(f"📊 Top 5 genres: {dict(sorted_genres[:5])}")
            logger.info(f"📊 Bottom 5 genres: {dict(sorted_genres[-5:])}")

            return coverage_stats

        except Exception as e:
            logger.error(f"Failed to compute genre coverage: {e}", exc_info=True)
            return {}

    async def get_rare_genres(self, threshold: float = 0.10) -> Dict[str, float]:
        """
        Zwraca gatunki rzadkie (<threshold coverage).

        Args:
            threshold: Próg coverage (domyślnie 0.10 = 10%)

        Returns:
            Dict[genre, coverage] dla gatunków <threshold
        """
        coverage_stats = await self._get_genre_coverage_stats()

        rare = {genre: cov for genre, cov in coverage_stats.items() if cov < threshold}

        logger.info(f"🔍 Found {len(rare)} rare genres (<{threshold:.0%} coverage)")

        return rare

    # ============================================================
    #  ✅ FIX #3: Genre profile Z NORMALIZACJĄ
    # ============================================================

    async def _get_user_genre_profile(self, user_id: str, limit: int = 50) -> Counter:
        """
        Analizuje historię użytkownika i zwraca profil gatunkowy.

        ✅ NOWE: Normalizuje gatunki przed zliczaniem!

        Returns:
            Counter z ZNORMALIZOWANYMI gatunkami i ich wagami
            (np. {"business": 7.0, "science": 3.0})
        """
        try:
            # Pobierz ostatnie interakcje użytkownika
            interactions = (
                await self.db.interactions.find({"user_id": user_id})
                .sort("created_at", -1)
                .limit(limit)
                .to_list(length=limit)
            )

            if not interactions:
                logger.debug(f"No interactions found for user {user_id[:12]}...")
                return Counter()

            # Zbierz book_ids
            book_ids = [ObjectId(i["book_id"]) for i in interactions]

            # Pobierz książki z bazy
            books = await self.db.books.find({"_id": {"$in": book_ids}}).to_list(
                length=len(book_ids)
            )

            # Mapuj book_id -> book
            book_map = {str(b["_id"]): b for b in books}

            # Zlicz gatunki z wagami z interakcji
            genre_counter = Counter()

            for interaction in interactions:
                book_id = interaction["book_id"]
                weight = interaction.get("weight", 1.0)
                book = book_map.get(book_id)

                if book:
                    # Obsłuż zarówno 'genre' jak i 'genres'
                    genres = book.get("genre", book.get("genres", []))

                    # Normalizuj do listy
                    if isinstance(genres, str):
                        genres = [genres]
                    elif not isinstance(genres, list):
                        genres = []

                    for genre in genres:
                        if genre:  # Skip empty strings
                            # ✅ NOWE: Normalizuj gatunek!
                            normalized = normalize_genre(genre)
                            genre_counter[normalized] += weight

            logger.info(
                f"📊 User {user_id[:12]}... genre profile: " f"{dict(genre_counter.most_common(5))}"
            )

            return genre_counter

        except Exception as e:
            logger.error(f"Failed to get user genre profile: {e}", exc_info=True)
            return Counter()

    async def _is_niche_user(
        self, genre_profile: Counter, threshold: float = 0.5, rare_coverage_threshold: float = 0.10
    ) -> bool:
        """
        🆕 COVERAGE-BASED: Wykrywa czy użytkownik ma niszowe preferencje.

        Zamiast hardcoded listy, automatycznie wykrywa gatunki rzadkie
        na podstawie coverage w bazie (<10% books).

        Args:
            genre_profile: Counter z gatunkami użytkownika (ZNORMALIZOWANE!)
            threshold: Próg % rzadkich gatunków (domyślnie 50%)
            rare_coverage_threshold: Próg coverage dla "rzadkich" (domyślnie 10%)

        Returns:
            True jeśli użytkownik ma >threshold rzadkich gatunków
        """
        if not genre_profile:
            return False

        # 1. Pobierz coverage stats (z cache)
        coverage_stats = await self._get_genre_coverage_stats()

        if not coverage_stats:
            logger.warning("No coverage stats available, falling back to hardcoded list")
            # Fallback do starej metody
            return self._is_niche_user_fallback(genre_profile, threshold)

        # 2. Automatycznie wykryj gatunki rzadkie
        rare_genres = {
            genre for genre, cov in coverage_stats.items() if cov < rare_coverage_threshold
        }

        logger.debug(
            f"🔍 Auto-detected {len(rare_genres)} rare genres (<{rare_coverage_threshold:.0%})"
        )

        # 3. Ile % użytkownika to rzadkie gatunki?
        total_weight = sum(genre_profile.values())
        rare_weight = sum(weight for genre, weight in genre_profile.items() if genre in rare_genres)

        rare_percentage = rare_weight / total_weight if total_weight > 0 else 0

        is_niche = rare_percentage > threshold

        if is_niche:
            # Pokaż które gatunki użytkownika są rzadkie
            user_rare_genres = {
                g: (w, coverage_stats.get(g, 0))
                for g, w in genre_profile.items()
                if g in rare_genres
            }

            logger.info(
                f"🎯 NICHE USER detected: {rare_percentage:.1%} rare genres "
                f"(coverage <{rare_coverage_threshold:.0%})"
            )
            logger.info(f"   User rare genres: {dict(list(user_rare_genres.items())[:3])}")
        else:
            logger.debug(
                f"📊 Regular user: {rare_percentage:.1%} rare genres (threshold={threshold:.0%})"
            )

        return is_niche

    def _is_niche_user_fallback(self, genre_profile: Counter, threshold: float = 0.5) -> bool:
        """
        Fallback method - hardcoded lista dla przypadku gdy coverage stats nie działa.

        ✅ NOWE: Lista ze znormalizowanymi gatunkami!
        """
        # Rozszerzona lista bazująca na znanym rozkładzie goodbooks-10k
        niche_genres = {
            # Core rare (<5% coverage) - ZNORMALIZOWANE
            "business",
            "science",
            "biography",
            "philosophy",
            "psychology",
            "history",
            "economics",
            "politics",
            "poetry",
            "science fiction",  # ← znormalizowane z "Sci Fi"
            "horror",
            "crime",
            "humor",
            # Extended rare (<10% coverage)
            "nonfiction",  # ← znormalizowane z "Non Fiction"
            "classics",
            "historical fiction",
            "thriller",
            "young adult",  # ← znormalizowane z "Ya"
            "paranormal",
            "childrens",
            "graphic novels",
            "comics",
            "graphic novel",
        }

        total_weight = sum(genre_profile.values())
        niche_weight = sum(w for g, w in genre_profile.items() if g in niche_genres)

        niche_pct = niche_weight / total_weight if total_weight > 0 else 0

        return niche_pct > threshold

    # ============================================================
    #  ✅ FIX #4: BOOST NISZOWE GATUNKI (zamiast top 3)
    # ============================================================

    async def _apply_genre_boosting(
        self, candidates: List[Dict], user_id: str, boost_factor: float = 3.0, top_n_genres: int = 6
    ) -> List[Dict]:
        """
        Aplikuje genre boosting do rekomendacji.

        ✅ FIX #4: Boostuje RARE gatunki z profilu użytkownika, nie top 3!
        ✅ FIX #3: Używa znormalizowanych gatunków!
        ✅ FIX #1: Podmienia score = boosted_score na końcu!

        Książki z rare/top gatunków użytkownika dostają boost do score.

        Args:
            candidates: Lista książek z scores z LightGCN
            user_id: MongoDB user_id
            boost_factor: Mnożnik dla matching books (domyślnie 3.0)
            top_n_genres: Ile gatunków brać z profilu (domyślnie 6)

        Returns:
            Posortowana lista z boosted scores
        """
        try:
            # 1. Pobierz profil użytkownika (ZNORMALIZOWANY!)
            user_profile = await self._get_user_genre_profile(user_id)

            if not user_profile:
                logger.debug("No genre profile, skipping boosting")
                return candidates

            # 2. Pobierz coverage stats
            coverage_stats = await self._get_genre_coverage_stats()
            rare_threshold = 0.10  # 10%

            # ============================================================
            # ✅ FIX #4: BOOST RARE GENRES z profilu użytkownika
            # ============================================================

            # 3. Zbierz RARE gatunki z profilu użytkownika (priorytet!)
            user_rare_genres = set()
            user_top_genres = set()

            for genre, score in user_profile.most_common(top_n_genres * 2):  # Sprawdź więcej
                norm_genre = normalize_genre(genre)  # ✅ Normalizuj
                coverage = coverage_stats.get(norm_genre, 0.0)

                if coverage < rare_threshold:
                    user_rare_genres.add(norm_genre)

                # Też zbierz top (ale rare mają priorytet)
                if len(user_top_genres) < top_n_genres:
                    user_top_genres.add(norm_genre)

            # 4. Użyj rare jeśli istnieją, inaczej top
            boost_genres = user_rare_genres if user_rare_genres else user_top_genres

            logger.info(
                f"🚀 Boosting genres: {boost_genres} "
                f"(rare: {len(user_rare_genres)}, top: {len(user_top_genres)})"
            )

            # 5. Pobierz book_ids z candidates
            book_ids = [c.get("_id") for c in candidates if c.get("_id")]

            if not book_ids:
                logger.warning("No book_ids in candidates")
                return candidates

            # 6. Pobierz książki z DB
            books_cursor = self.db.books.find(
                {"_id": {"$in": [self._to_object_id(bid) for bid in book_ids]}}
            )
            books = await books_cursor.to_list(length=len(book_ids))

            # 7. Mapuj book_id -> ZNORMALIZOWANE genres
            book_genres_map = {}
            for book in books:
                book_id = str(book["_id"])
                genres = book.get("genre", book.get("genres", []))

                # Normalizuj do listy
                if isinstance(genres, str):
                    genres = [genres]
                elif not isinstance(genres, list):
                    genres = []

                # ✅ FIX #3: Normalizuj gatunki książki!
                book_genres_map[book_id] = set(normalize_genre(g) for g in genres if g)

            # 8. Aplikuj boosting
            boosted_count = 0
            for candidate in candidates:
                book_id = candidate.get("_id")
                if not book_id:
                    continue

                book_genres = book_genres_map.get(book_id, set())

                # ✅ Match ze znormalizowanymi gatunkami
                matching_genres = book_genres & boost_genres

                if matching_genres:
                    # Boost proporcjonalny do liczby matching genres
                    original_score = candidate.get("score", 0.5)
                    boost = boost_factor ** len(matching_genres)

                    candidate["boosted_score"] = original_score * boost
                    candidate["boosted"] = True
                    candidate["matching_genres"] = list(matching_genres)

                    boosted_count += 1
                else:
                    candidate["boosted_score"] = candidate.get("score", 0.5)
                    candidate["boosted"] = False

            # ============================================================
            # ✅ FIX #1: PODMIEŃ score = boosted_score (dla MMR!)
            # ============================================================
            for candidate in candidates:
                candidate["score"] = candidate.get("boosted_score", candidate.get("score", 0.0))

            # 9. Sortuj po boosted_score (teraz score)
            candidates.sort(key=lambda x: x.get("score", 0), reverse=True)

            logger.info(
                f"✅ Genre boosting complete: {boosted_count}/{len(candidates)} books boosted "
                f"(factor={boost_factor})"
            )

            return candidates

        except Exception as e:
            logger.error(f"Genre boosting failed: {e}", exc_info=True)
            # Fallback: zwróć bez zmian
            return candidates

    async def get_content_based_recommendations(self, user_id: str, n: int = 10) -> List[Dict]:

        try:
            interactions = (
                await self.db.interactions.find(
                    {"user_id": user_id, "interaction_type": {"$in": ["borrow", "review"]}}
                )
                .sort("created_at", -1)
                .limit(50)
                .to_list(length=50)
            )

            if not interactions:
                return await self._get_popular_books(n)

            interacted_book_ids = [i["book_id"] for i in interactions]

            books = await self.db.books.find(
                {"_id": {"$in": [self._to_object_id(bid) for bid in interacted_book_ids]}}
            ).to_list(length=len(interacted_book_ids))

            genre_counts = {}
            author_counts = {}

            for book in books:
                book = enrich_book_contract(book)
                for genre in get_genres(book):
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1

                for author in get_authors(book):
                    author_counts[author] = author_counts.get(author, 0) + 1

            top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            logger.info(
                f"📊 User {user_id[:12]}... preferences: genres={[g[0] for g in top_genres]}, authors={[a[0] for a in top_authors]}"
            )

            query = {"$or": []}

            if top_genres:
                genre_values = [g[0] for g in top_genres]
                query["$or"].append({"genre": {"$in": genre_values}})
                query["$or"].append({"genres": {"$in": genre_values}})

            if top_authors:
                author_values = [a[0] for a in top_authors]
                query["$or"].append({"author": {"$in": author_values}})
                query["$or"].append({"authors": {"$in": author_values}})

            if not query["$or"]:
                return await self._get_popular_books(n)

            query["_id"] = {"$nin": [self._to_object_id(bid) for bid in interacted_book_ids]}

            matching_books = await self.db.books.find(query).limit(n * 2).to_list(length=n * 2)

            scored = []
            for book in matching_books:
                book = enrich_book_contract(book)
                score = 0.0
                reasons = []

                for genre in get_genres(book):
                    if genre in genre_counts:
                        score += genre_counts[genre] * 0.5
                        reasons.append(f"Genre: {genre}")

                for author in get_authors(book):
                    if author in author_counts:
                        score += author_counts[author] * 0.3
                        reasons.append(f"Author: {author}")

                score += book.get("average_rating", 0) * 0.2

                scored.append(
                    {
                        "book_id": str(book["_id"]),
                        "score": score,
                        "reason": " | ".join(reasons[:2]) if reasons else "Popular book",
                    }
                )

            scored.sort(key=lambda x: x["score"], reverse=True)

            logger.info(
                f"✅ Generated {len(scored[:n])} content-based recommendations for user {user_id[:12]}..."
            )

            return scored[:n]

        except Exception as e:
            logger.error(f"❌ Content-based recommendations failed: {e}", exc_info=True)
            return await self._get_popular_books(n)

    async def _get_user_content_profile(self, user_id: str, limit: int = 80) -> Dict:
        interactions = (
            await self.db.interactions.find(
                {"user_id": user_id, "interaction_type": {"$in": ["borrow", "review"]}}
            )
            .sort("created_at", -1)
            .limit(limit)
            .to_list(length=limit)
        )

        if not interactions:
            return {"genres": Counter(), "authors": Counter(), "clusters": Counter()}

        book_ids = [
            self._to_object_id(interaction["book_id"])
            for interaction in interactions
            if interaction.get("book_id")
        ]
        books = await self.db.books.find({"_id": {"$in": book_ids}}).to_list(length=len(book_ids))
        book_map = {str(book["_id"]): enrich_book_contract(book) for book in books}

        genre_counter = Counter()
        author_counter = Counter()
        cluster_counter = Counter()

        type_weights = {"borrow": 1.0, "review": 0.8}
        for interaction in interactions:
            book = book_map.get(str(interaction.get("book_id")))
            if not book:
                continue

            weight = type_weights.get(interaction.get("interaction_type"), 0.5)
            for genre in book.get("canonical_genres", []):
                genre_counter[genre] += weight
            for author in get_authors(book):
                author_counter[author] += weight
            for cluster in book.get("recommendation_clusters", []):
                cluster_counter[cluster] += weight

        return {"genres": genre_counter, "authors": author_counter, "clusters": cluster_counter}

    async def get_cluster_limits(self, user_id: str, n: int) -> Dict[str, int]:
        profile = await self._get_user_content_profile(user_id)
        has_comics_signal = profile["clusters"].get("comics_manga", 0) > 0

        if has_comics_signal:
            comics_limit = max(4, int(math.ceil(n * 0.40)))
        else:
            comics_limit = 2

        return {"comics_manga": comics_limit}

    async def apply_hybrid_scoring(
        self, candidates: List[Dict], user_id: str, relevance_weight: float = 0.70
    ) -> List[Dict]:
        if not candidates:
            return candidates

        profile = await self._get_user_content_profile(user_id)
        genre_total = sum(profile["genres"].values()) or 0.0
        author_total = sum(profile["authors"].values()) or 0.0
        cluster_total = sum(profile["clusters"].values()) or 0.0

        raw_scores = [float(candidate.get("score", 0.0) or 0.0) for candidate in candidates]
        min_score = min(raw_scores)
        max_score = max(raw_scores)
        score_range = max_score - min_score

        for candidate in candidates:
            candidate = enrich_book_contract(candidate)
            lightgcn_score = float(candidate.get("score", 0.0) or 0.0)
            if score_range > 0:
                lightgcn_norm = (lightgcn_score - min_score) / score_range
            else:
                lightgcn_norm = 1.0

            genre_score = 0.0
            if genre_total:
                genre_score = (
                    sum(
                        profile["genres"].get(genre, 0.0)
                        for genre in candidate.get("canonical_genres", [])
                    )
                    / genre_total
                )

            author_score = 0.0
            if author_total:
                author_score = (
                    sum(profile["authors"].get(author, 0.0) for author in get_authors(candidate))
                    / author_total
                )

            cluster_score = 0.0
            if cluster_total:
                cluster_score = (
                    sum(
                        profile["clusters"].get(cluster, 0.0)
                        for cluster in candidate.get("recommendation_clusters", [])
                    )
                    / cluster_total
                )

            profile_score = min(
                1.0, genre_score * 0.55 + author_score * 0.30 + cluster_score * 0.15
            )
            rating_score = min(float(candidate.get("average_rating", 0.0) or 0.0) / 5.0, 1.0)
            popularity = float(candidate.get("ratings_count", 0.0) or 0.0)
            popularity_score = min(math.log1p(popularity) / math.log1p(5_000_000), 1.0)
            quality_score = rating_score * 0.75 + popularity_score * 0.25

            candidate["lightgcn_score"] = lightgcn_score
            candidate["content_score"] = profile_score
            candidate["quality_score"] = quality_score
            candidate["score"] = (
                relevance_weight * lightgcn_norm
                + 0.25 * profile_score
                + (1.0 - relevance_weight - 0.25) * quality_score
            )

        candidates.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return candidates

    async def update_user_embedding_incremental(
        self, user_id: str, book_id: str, interaction_weight: float
    ) -> Dict:

        return await self.adapter.update_user_embedding_incremental(
            user_id=user_id, book_id=book_id, interaction_weight=interaction_weight
        )

    def _get_or_create_user_index(self, mongo_user_id: str) -> int:

        if hasattr(self.lightgcn, "get_or_create_user_idx"):
            return self.lightgcn.get_or_create_user_idx(mongo_user_id)
        else:
            logger.warning("⚠️  GoodbooksLightGCNService doesn't have get_or_create_user_idx method")
            return None

    async def get_user_embedding_info(self, user_id: str) -> Dict:

        try:
            user_idx = None
            if hasattr(self.lightgcn, "mongo_user_to_idx"):
                user_idx = self.lightgcn.mongo_user_to_idx.get(user_id)

            has_model_index = user_idx is not None

            user_emb_doc = await self.db.user_embeddings.find_one({"user_id": user_id})
            has_mongodb_embedding = user_emb_doc is not None

            interactions_count = await self.db.interactions.count_documents({"user_id": user_id})

            is_cold_start = interactions_count < 5

            embeddings_updated_count = await self.db.interactions.count_documents(
                {"user_id": user_id, "embedding_updated": True}
            )

            total_model_users = 0
            if hasattr(self.lightgcn, "mongo_user_to_idx"):
                total_model_users = len(self.lightgcn.mongo_user_to_idx)

            return {
                "user_id": user_id,
                "has_model_index": has_model_index,
                "model_index": user_idx,
                "has_mongodb_embedding": has_mongodb_embedding,
                "embedding_last_updated": (
                    user_emb_doc["last_updated"].isoformat()
                    if user_emb_doc and "last_updated" in user_emb_doc
                    else None
                ),
                "interaction_count_mongodb": (
                    user_emb_doc.get("interaction_count", 0) if user_emb_doc else 0
                ),
                "interaction_count_actual": interactions_count,
                "embeddings_updated_count": embeddings_updated_count,
                "is_cold_start": is_cold_start,
                "total_model_users": total_model_users,
                "recommendation": (
                    "All good!"
                    if has_model_index and interactions_count > 5
                    else "Add more interactions (borrow/review books) to improve recommendations"
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get embedding info: {e}")
            return {"user_id": user_id, "error": str(e)}

    async def _get_popular_books(self, n: int = 10) -> List[Dict]:
        try:
            popular = (
                await self.db.books.find({}).sort("average_rating", -1).limit(n).to_list(length=n)
            )

            return [
                {
                    "book_id": str(book["_id"]),
                    "score": book.get("average_rating", 0),
                    "reason": "Popular book",
                }
                for book in popular
            ]
        except Exception as e:
            logger.error(f"Failed to get popular books: {e}")
            return []

    def _to_object_id(self, id_value):
        """Convert string to ObjectId if valid, otherwise return as-is"""
        if isinstance(id_value, str) and ObjectId.is_valid(id_value):
            return ObjectId(id_value)
        return id_value


_recommendation_service_instance = None


def get_recommendation_service() -> Optional[RecommendationService]:
    global _recommendation_service_instance
    return _recommendation_service_instance


def initialize_recommendation_service(lightgcn_service, lightgcn_adapter, db):

    global _recommendation_service_instance

    if _recommendation_service_instance is not None:
        logger.warning("RecommendationService already initialized")
        return _recommendation_service_instance

    _recommendation_service_instance = RecommendationService(
        lightgcn_service=lightgcn_service, lightgcn_adapter=lightgcn_adapter, db=db
    )

    logger.info("✅ RecommendationService initialized with COVERAGE-BASED GENRE BOOSTING! 🚀")

    return _recommendation_service_instance
