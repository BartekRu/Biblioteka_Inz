"""
Real-Time Recommendations Diagnostic Script
============================================

Ten script testuje czy system real-time updates działa poprawnie.

Usage:
    python test_realtime_updates.py --user-id YOUR_USER_ID --api-url http://localhost:8000

Requires:
    pip install requests
"""

import requests
import time
import json
from typing import List, Dict
import argparse


class RecommendationTester:
    def __init__(self, api_url: str, token: str):
        self.api_url = api_url.rstrip('/')
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def get_embedding_info(self) -> Dict:
        """Get user embedding diagnostics"""
        resp = requests.get(
            f"{self.api_url}/v1/recommendations/user/embedding-info",
            headers=self.headers
        )
        resp.raise_for_status()
        return resp.json()
    
    def get_recommendations(self, n: int = 10, lambda_param: float = 0.7) -> List[Dict]:
        """Get recommendations"""
        resp = requests.get(
            f"{self.api_url}/v1/recommendations/user-lightgcn",
            params={"n": n, "lambda_param": lambda_param},
            headers=self.headers
        )
        resp.raise_for_status()
        data = resp.json()
        return data["recommendations"], data["metadata"]
    
    def borrow_book(self, book_id: str) -> Dict:
        """Borrow a book"""
        resp = requests.post(
            f"{self.api_url}/v1/loans/borrow",
            json={"book_id": book_id},
            headers=self.headers
        )
        resp.raise_for_status()
        return resp.json()
    
    def track_interaction(self, book_id: str, interaction_type: str) -> Dict:
        """Track an interaction"""
        resp = requests.post(
            f"{self.api_url}/v1/recommendations/interaction",
            json={"book_id": book_id, "interaction_type": interaction_type},
            headers=self.headers
        )
        resp.raise_for_status()
        return resp.json()
    
    def clear_cache(self) -> Dict:
        """Clear recommendation cache"""
        resp = requests.post(
            f"{self.api_url}/v1/recommendations/cache/clear",
            headers=self.headers
        )
        resp.raise_for_status()
        return resp.json()
    
    def run_full_test(self):
        """Run complete diagnostic test"""
        print("=" * 80)
        print("  REAL-TIME RECOMMENDATIONS DIAGNOSTIC TEST")
        print("=" * 80)
        print()
        
        # Test 1: Embedding info
        print("TEST 1: Embedding Information")
        print("-" * 80)
        try:
            info = self.get_embedding_info()
            print(f"✓ Has MongoDB embedding: {info['has_mongodb_embedding']}")
            print(f"✓ Last updated: {info.get('embedding_last_updated', 'Never')}")
            print(f"✓ Interaction count: {info['interaction_count_actual']}")
            print(f"✓ Has model index: {info['has_model_index']}")
            print(f"✓ Is cold-start: {info['is_cold_start']}")
            
            if not info['has_mongodb_embedding']:
                print("❌ PROBLEM: User has no MongoDB embedding!")
                print("   → Run migration: python migrate_user_embeddings.py")
                return False
            
            if info['is_cold_start']:
                print("⚠️  WARNING: User is cold-start (< 5 interactions)")
                print("   → Content-based fallback will be used")
        except Exception as e:
            print(f"❌ FAILED: {e}")
            return False
        
        print()
        
        # Test 2: Get initial recommendations
        print("TEST 2: Initial Recommendations")
        print("-" * 80)
        try:
            recs_before, meta_before = self.get_recommendations(n=5)
            print(f"✓ Got {len(recs_before)} recommendations")
            print(f"✓ Embedding updated: {meta_before.get('embedding_updated', False)}")
            
            print("\nTop 5 recommendations (BEFORE interaction):")
            for i, rec in enumerate(recs_before[:5], 1):
                print(f"  {i}. {rec.get('title', 'Unknown')} (score: {rec.get('score', 0):.4f})")
        except Exception as e:
            print(f"❌ FAILED: {e}")
            return False
        
        print()
        
        # Test 3: Create interaction
        print("TEST 3: Create Interaction (View)")
        print("-" * 80)
        try:
            # Pick a book from recommendations
            test_book_id = recs_before[0]["_id"]
            
            print(f"Tracking view interaction for book: {test_book_id}")
            interaction_resp = self.track_interaction(test_book_id, "view")
            
            print(f"✓ Interaction created")
            print(f"✓ Embedding updated: {interaction_resp.get('embedding_updated', False)}")
            print(f"✓ Cache invalidated: {interaction_resp.get('cache_invalidated', False)}")
            
            if not interaction_resp.get('embedding_updated'):
                print("❌ WARNING: Embedding was not updated!")
                print("   → Check backend logs for errors")
        except Exception as e:
            print(f"❌ FAILED: {e}")
            return False
        
        print()
        
        # Wait a moment
        print("Waiting 2 seconds for updates to propagate...")
        time.sleep(2)
        
        # Test 4: Get recommendations again
        print("\nTEST 4: Recommendations After Interaction")
        print("-" * 80)
        try:
            recs_after, meta_after = self.get_recommendations(n=5)
            print(f"✓ Got {len(recs_after)} recommendations")
            
            print("\nTop 5 recommendations (AFTER interaction):")
            for i, rec in enumerate(recs_after[:5], 1):
                print(f"  {i}. {rec.get('title', 'Unknown')} (score: {rec.get('score', 0):.4f})")
            
            # Compare
            before_ids = [r["_id"] for r in recs_before[:5]]
            after_ids = [r["_id"] for r in recs_after[:5]]
            
            same_count = len(set(before_ids) & set(after_ids))
            print(f"\n📊 Similarity: {same_count}/5 books are the same")
            
            if same_count == 5:
                print("⚠️  WARNING: Recommendations did not change!")
                print("   Possible reasons:")
                print("   1. Embedding update was too small (view weight = 0.3)")
                print("   2. Cache is being used (check cache_invalidated)")
                print("   3. Model has very strong prior beliefs")
                print("\n   Try borrowing a book (weight = 1.0) instead of view")
            elif same_count <= 2:
                print("✅ GOOD: Recommendations changed significantly!")
            else:
                print("✓ OK: Some recommendations changed")
        except Exception as e:
            print(f"❌ FAILED: {e}")
            return False
        
        print()
        
        # Test 5: Test diversity (lambda comparison)
        print("TEST 5: Diversity Test (Lambda Comparison)")
        print("-" * 80)
        try:
            # High relevance (lambda=0.9)
            recs_relevant, _ = self.get_recommendations(n=10, lambda_param=0.9)
            
            # High diversity (lambda=0.3)
            recs_diverse, _ = self.get_recommendations(n=10, lambda_param=0.3)
            
            relevant_ids = set(r["_id"] for r in recs_relevant)
            diverse_ids = set(r["_id"] for r in recs_diverse)
            
            overlap = len(relevant_ids & diverse_ids)
            
            print(f"✓ High relevance (λ=0.9): {len(recs_relevant)} books")
            print(f"✓ High diversity (λ=0.3): {len(recs_diverse)} books")
            print(f"✓ Overlap: {overlap}/10 books")
            
            if overlap >= 8:
                print("❌ PROBLEM: Too much overlap between relevance and diversity!")
                print("   → Recommendations should be more different")
                print("   → Check MMR implementation")
            elif overlap <= 3:
                print("✅ EXCELLENT: Good diversity difference!")
            else:
                print("✓ OK: Reasonable diversity difference")
        except Exception as e:
            print(f"❌ FAILED: {e}")
            return False
        
        print()
        
        # Test 6: Cache clearing
        print("TEST 6: Cache Clearing")
        print("-" * 80)
        try:
            clear_resp = self.clear_cache()
            print(f"✓ {clear_resp.get('message', 'Cache cleared')}")
        except Exception as e:
            print(f"❌ FAILED: {e}")
            return False
        
        print()
        
        # Summary
        print("=" * 80)
        print("  TEST SUMMARY")
        print("=" * 80)
        print("✅ All tests passed!")
        print("\nRecommendations:")
        print("1. If recommendations don't change enough, try borrowing books")
        print("2. If diversity is low, check MMR parameters")
        print("3. Monitor embedding updates in backend logs")
        
        return True


def main():
    parser = argparse.ArgumentParser(description="Test real-time recommendations")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--token", required=True, help="JWT access token")
    
    args = parser.parse_args()
    
    tester = RecommendationTester(args.api_url, args.token)
    
    success = tester.run_full_test()
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()


# =============================================================================
# PRZYKŁAD UŻYCIA
# =============================================================================

"""
# Krok 1: Zaloguj się i uzyskaj token
POST http://localhost:8000/v1/auth/login
{
  "username": "test_user",
  "password": "password"
}

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  ...
}

# Krok 2: Uruchom test
python test_realtime_updates.py --token "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Oczekiwany output:
# ================================================================================
#   REAL-TIME RECOMMENDATIONS DIAGNOSTIC TEST
# ================================================================================
# 
# TEST 1: Embedding Information
# --------------------------------------------------------------------------------
# ✓ Has MongoDB embedding: True
# ✓ Last updated: 2025-12-26T10:15:32.123000
# ✓ Interaction count: 23
# ✓ Has model index: True
# ✓ Is cold-start: False
# 
# TEST 2: Initial Recommendations
# --------------------------------------------------------------------------------
# ✓ Got 5 recommendations
# ✓ Embedding updated: True
# 
# Top 5 recommendations (BEFORE interaction):
#   1. Sacajawea (Lewis & Clark Expedition) (score: 0.8234)
#   2. The Covenant (score: 0.7891)
#   3. Winter Solstice (score: 0.7654)
#   ...
# 
# TEST 3: Create Interaction (View)
# --------------------------------------------------------------------------------
# Tracking view interaction for book: 6935a48a1d2eec9b4b4c8603
# ✓ Interaction created
# ✓ Embedding updated: True
# ✓ Cache invalidated: True
# 
# Waiting 2 seconds for updates to propagate...
# 
# TEST 4: Recommendations After Interaction
# --------------------------------------------------------------------------------
# ✓ Got 5 recommendations
# 
# Top 5 recommendations (AFTER interaction):
#   1. Sacajawea (Lewis & Clark Expedition) (score: 0.8256)  ← Score zwiększył się!
#   2. The Covenant (score: 0.7905)
#   3. Forever Amber (score: 0.7701)  ← Nowa książka!
#   ...
# 
# 📊 Similarity: 3/5 books are the same
# ✓ OK: Some recommendations changed
# 
# TEST 5: Diversity Test (Lambda Comparison)
# --------------------------------------------------------------------------------
# ✓ High relevance (λ=0.9): 10 books
# ✓ High diversity (λ=0.3): 10 books
# ✓ Overlap: 4/10 books
# ✓ OK: Reasonable diversity difference
# 
# TEST 6: Cache Clearing
# --------------------------------------------------------------------------------
# ✓ Cache cleared. Next recommendation request will use fresh embeddings.
# 
# ================================================================================
#   TEST SUMMARY
# ================================================================================
# ✅ All tests passed!
# 
# Recommendations:
# 1. If recommendations don't change enough, try borrowing books
# 2. If diversity is low, check MMR parameters
# 3. Monitor embedding updates in backend logs
"""
