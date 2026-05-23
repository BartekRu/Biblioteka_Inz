import unittest

from app.utils.book_contract import enrich_book_contract
from recommendation_engine.mmr_reranking import diversity_metrics, mmr_rerank


class RecommendationContractTests(unittest.TestCase):
    def test_normalize_book_adds_author_and_genre_contract(self):
        book = enrich_book_contract(
            {
                "_id": "1",
                "title": "Naruto, Vol. 05: Exam Hell (Naruto, #5)",
                "author": "Masashi Kishimoto",
                "genre": ["Manga", "Fantasy", "Comics"],
            }
        )

        self.assertEqual(book["authors"], ["Masashi Kishimoto"])
        self.assertEqual(book["genres"], ["Manga", "Fantasy", "Comics"])
        self.assertIn("comics_manga", book["recommendation_clusters"])
        self.assertEqual(book["series_key"], "naruto")

    def test_mmr_uses_author_fallback_and_limits_repeats(self):
        candidates = [
            {
                "_id": "1",
                "title": "Naruto, Vol. 1 (Naruto, #1)",
                "author": "Masashi Kishimoto",
                "genre": ["Manga", "Fantasy"],
                "score": 1.0,
            },
            {
                "_id": "2",
                "title": "Naruto, Vol. 2 (Naruto, #2)",
                "author": "Masashi Kishimoto",
                "genre": ["Manga", "Fantasy"],
                "score": 0.99,
            },
            {
                "_id": "3",
                "title": "Naruto, Vol. 3 (Naruto, #3)",
                "author": "Masashi Kishimoto",
                "genre": ["Manga", "Fantasy"],
                "score": 0.98,
            },
            {
                "_id": "4",
                "title": "Dune (Dune, #1)",
                "author": "Frank Herbert",
                "genre": ["Science Fiction"],
                "score": 0.60,
            },
            {
                "_id": "5",
                "title": "1984",
                "author": "George Orwell",
                "genre": ["Classics", "Fiction"],
                "score": 0.55,
            },
        ]

        candidates = [enrich_book_contract(candidate) for candidate in candidates]
        reranked = mmr_rerank(
            candidates,
            n=4,
            lambda_param=0.7,
            enforce_author_limit=True,
            max_per_author=2,
            max_per_series=2,
            cluster_limits={"comics_manga": 2},
        )
        metrics = diversity_metrics(reranked)

        self.assertGreater(metrics["unique_authors"], 1)
        self.assertLessEqual(
            sum(1 for book in reranked if book["author"] == "Masashi Kishimoto"),
            2,
        )
        self.assertLessEqual(metrics["cluster_counts"].get("comics_manga", 0), 2)


if __name__ == "__main__":
    unittest.main()
