"""
test_incremental_updates.py

Skrypt testowy dla Real-time Incremental Updates
=================================================

Testuje:
1. Inicjalizację serwisu
2. Tworzenie nowych użytkowników
3. Aktualizację embeddingów po interakcjach
4. Cache i invalidację
5. Checkpoint save

Użycie:
    python test_incremental_updates.py
"""

import sys
sys.path.append(".")

from recommendation_engine.incremental_lightgcn_service import get_incremental_service
import numpy as np
from datetime import datetime


def test_service_initialization():
    """Test 1: Inicjalizacja serwisu"""
    print("\n" + "="*60)
    print("TEST 1: Service Initialization")
    print("="*60)
    
    service = get_incremental_service()
    stats = service.get_stats()
    
    print(f"✅ Service loaded: {stats['is_loaded']}")
    print(f"✅ Base users: {stats['base_users']:,}")
    print(f"✅ Total users: {stats['total_users']:,}")
    print(f"✅ Total books: {stats['total_books']:,}")
    print(f"✅ Embedding dim: {stats['embedding_dim']}")
    
    assert stats['is_loaded'], "Service should be loaded"
    assert stats['total_books'] > 0, "Should have books"
    
    print("\n✅ Test 1 PASSED!\n")
    return service


def test_new_user_creation(service):
    """Test 2: Tworzenie nowego użytkownika"""
    print("\n" + "="*60)
    print("TEST 2: New User Creation")
    print("="*60)
    
    # Symuluj nowego użytkownika
    fake_user_id = f"test_user_{datetime.now().timestamp()}"
    
    print(f"📝 Creating user: {fake_user_id}")
    
    initial_user_count = len(service.user_embeddings)
    user_idx = service.get_or_create_user_idx(fake_user_id)
    final_user_count = len(service.user_embeddings)
    
    print(f"✅ User index: {user_idx}")
    print(f"✅ Users before: {initial_user_count:,}")
    print(f"✅ Users after: {final_user_count:,}")
    
    assert final_user_count == initial_user_count + 1, "Should create exactly 1 new user"
    assert user_idx in service.idx_to_mongo_user, "Should map idx -> user_id"
    assert fake_user_id in service.mongo_user_to_idx, "Should map user_id -> idx"
    
    # Test idempotencji
    user_idx_2 = service.get_or_create_user_idx(fake_user_id)
    assert user_idx == user_idx_2, "Should return same index for same user"
    assert len(service.user_embeddings) == final_user_count, "Should not create duplicate"
    
    print("\n✅ Test 2 PASSED!\n")
    return fake_user_id, user_idx


def test_embedding_update(service, user_idx):
    """Test 3: Aktualizacja embeddingu"""
    print("\n" + "="*60)
    print("TEST 3: Embedding Update")
    print("="*60)
    
    # Wybierz losową książkę
    book_idx = np.random.randint(0, len(service.item_embeddings))
    
    print(f"📚 Book index: {book_idx}")
    print(f"👤 User index: {user_idx}")
    
    # Embedding przed
    embedding_before = service.user_embeddings[user_idx].copy()
    score_before = np.dot(embedding_before, service.item_embeddings[book_idx])
    
    print(f"📊 Score before: {score_before:.4f}")
    
    # Update
    update_info = service.update_user_embedding(
        user_idx=user_idx,
        book_idx=book_idx,
        interaction_type="borrow"
    )
    
    # Embedding po
    embedding_after = service.user_embeddings[user_idx]
    score_after = np.dot(embedding_after, service.item_embeddings[book_idx])
    
    print(f"📊 Score after: {score_after:.4f}")
    print(f"📈 Score change: {score_after - score_before:+.4f}")
    print(f"🔄 Update magnitude: {update_info['update_magnitude']:.6f}")
    
    # Assertions
    assert not np.allclose(embedding_before, embedding_after), "Embedding should change"
    assert score_after > score_before, "Score should increase for positive interaction"
    assert update_info['total_updates'] > 0, "Should track updates"
    
    print("\n✅ Test 3 PASSED!\n")
    return book_idx


def test_multiple_interactions(service, user_idx):
    """Test 4: Wiele interakcji - sprawdź czy embedding "uczy się" """
    print("\n" + "="*60)
    print("TEST 4: Multiple Interactions Learning")
    print("="*60)
    
    # Wybierz 3 książki
    book_indices = np.random.choice(len(service.item_embeddings), 3, replace=False)
    
    print(f"📚 Testing with books: {book_indices}")
    
    # Scores przed
    scores_before = []
    for book_idx in book_indices:
        score = np.dot(service.user_embeddings[user_idx], service.item_embeddings[book_idx])
        scores_before.append(score)
    
    print(f"📊 Scores before: {[f'{s:.4f}' for s in scores_before]}")
    
    # Symuluj 5 interakcji z każdą książką
    for _ in range(5):
        for book_idx in book_indices:
            service.update_user_embedding(
                user_idx=user_idx,
                book_idx=book_idx,
                interaction_type="borrow"
            )
    
    # Scores po
    scores_after = []
    for book_idx in book_indices:
        score = np.dot(service.user_embeddings[user_idx], service.item_embeddings[book_idx])
        scores_after.append(score)
    
    print(f"📊 Scores after:  {[f'{s:.4f}' for s in scores_after]}")
    print(f"📈 Changes:       {[f'{s:.4f}' for s in np.array(scores_after) - np.array(scores_before)]}")
    
    # Wszystkie scores powinny wzrosnąć
    improvements = [after > before for before, after in zip(scores_before, scores_after)]
    
    assert all(improvements), "All scores should improve"
    
    print("\n✅ Test 4 PASSED!\n")


def test_recommendations_cache(service, fake_user_id):
    """Test 5: Cache rekomendacji"""
    print("\n" + "="*60)
    print("TEST 5: Recommendations Cache")
    print("="*60)
    
    # Generuj rekomendacje
    recs1 = service.get_recommendations_for_user(
        mongo_user_id=fake_user_id,
        n=10,
        use_cache=True
    )
    
    print(f"✅ Generated {len(recs1)} recommendations")
    
    # Sprawdź cache
    cache_key = f"{fake_user_id}:10"
    assert cache_key in service.recommendations_cache, "Should cache recommendations"
    
    # Pobierz ponownie (z cache)
    import time
    start = time.time()
    recs2 = service.get_recommendations_for_user(
        mongo_user_id=fake_user_id,
        n=10,
        use_cache=True
    )
    cache_time = time.time() - start
    
    print(f"✅ Cache retrieval time: {cache_time*1000:.2f}ms")
    
    assert recs1 == recs2, "Cached results should be identical"
    assert cache_time < 0.01, "Cache should be very fast"
    
    # Invalidate cache
    service.invalidate_user_cache(fake_user_id)
    assert cache_key not in service.recommendations_cache, "Should invalidate cache"
    
    print("\n✅ Test 5 PASSED!\n")


def test_process_interaction_full_pipeline(service):
    """Test 6: Pełny pipeline process_interaction"""
    print("\n" + "="*60)
    print("TEST 6: Full Interaction Pipeline")
    print("="*60)
    
    fake_user_id = f"test_user_pipeline_{datetime.now().timestamp()}"
    
    # Wybierz książkę z goodbooks (musi być w mappingu)
    # Weź pierwszy książkę z mappingu
    first_goodbooks_id = None
    for gb_id in service.book_mapping.get('to_internal', {}).keys():
        first_goodbooks_id = int(gb_id)
        break
    
    if first_goodbooks_id is None:
        print("⚠️  No books in mapping - skipping test")
        return
    
    print(f"👤 User: {fake_user_id}")
    print(f"📚 Book (goodbooks_id): {first_goodbooks_id}")
    
    # Process interaction
    result = service.process_interaction(
        mongo_user_id=fake_user_id,
        goodbooks_book_id=first_goodbooks_id,
        interaction_type="borrow"
    )
    
    print(f"✅ Success: {result['success']}")
    print(f"✅ User idx: {result.get('user_idx')}")
    print(f"✅ Book idx: {result.get('book_idx')}")
    print(f"✅ Score after: {result['update_info']['score_after']:.4f}")
    
    assert result['success'], "Interaction should succeed"
    assert result['user_idx'] is not None, "Should have user_idx"
    assert result['book_idx'] is not None, "Should have book_idx"
    
    print("\n✅ Test 6 PASSED!\n")


def test_checkpoint_threshold(service):
    """Test 7: Checkpoint threshold"""
    print("\n" + "="*60)
    print("TEST 7: Checkpoint System")
    print("="*60)
    
    current_interactions = service.interactions_since_checkpoint
    threshold = service.checkpoint_interval
    
    print(f"📊 Interactions since checkpoint: {current_interactions}")
    print(f"🎯 Checkpoint threshold: {threshold}")
    
    should_checkpoint = service.should_checkpoint()
    print(f"💾 Should checkpoint: {should_checkpoint}")
    
    # Test checkpoint save (bez faktycznego zapisu - tylko sprawdź metodę)
    if should_checkpoint:
        print("⚠️  Checkpoint would trigger - skipping actual save in test")
    
    print("\n✅ Test 7 PASSED!\n")


def run_all_tests():
    """Uruchom wszystkie testy"""
    print("\n" + "="*60)
    print("🧪 INCREMENTAL LIGHTGCN - TEST SUITE")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test 1
        service = test_service_initialization()
        
        # Test 2
        fake_user_id, user_idx = test_new_user_creation(service)
        
        # Test 3
        book_idx = test_embedding_update(service, user_idx)
        
        # Test 4
        test_multiple_interactions(service, user_idx)
        
        # Test 5
        test_recommendations_cache(service, fake_user_id)
        
        # Test 6
        test_process_interaction_full_pipeline(service)
        
        # Test 7
        test_checkpoint_threshold(service)
        
        # Summary
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        
        final_stats = service.get_stats()
        print(f"\nFinal Statistics:")
        print(f"  Total users: {final_stats['total_users']:,}")
        print(f"  New users created: {final_stats['new_users_created']}")
        print(f"  Total updates: {final_stats['total_updates']:,}")
        print(f"  Cache size: {final_stats['cache_size']}")
        print(f"  Interactions since checkpoint: {final_stats['interactions_since_checkpoint']}")
        
        return True
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ TEST FAILED!")
        print("="*60)
        print(f"Error: {e}")
        
        import traceback
        traceback.print_exc()
        
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
