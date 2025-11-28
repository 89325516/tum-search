import visual_rank_engine
import numpy as np

def test_pagerank():
    print("Testing visual_rank_engine...")
    
    # Mock Data
    ids = ["A", "B", "C"]
    # Simple vectors: A close to B, C far away
    vectors = [
        [1.0, 0.0, 0.0], # A
        [0.9, 0.1, 0.0], # B
        [0.0, 0.0, 1.0]  # C
    ]
    
    # Interaction weights
    interaction_weights = {
        "A": 1.0,
        "B": 2.0, # B is popular
        "C": 1.0
    }
    
    # Transitions: A -> B
    transitions = {
        "A": {"B": 5}
    }
    
    m_neighbors = 2
    damping = 0.85
    iterations = 30
    
    try:
        ranks = visual_rank_engine.calculate_hnsw_pagerank(
            ids,
            vectors,
            interaction_weights,
            transitions,
            m_neighbors,
            damping,
            iterations
        )
        
        print("Calculation successful!")
        print("Ranks:", ranks)
        
        # Basic assertions
        assert len(ranks) == 3
        assert abs(sum(ranks.values()) - 1.0) < 1e-4
        
        # B should have high rank due to weight and transition from A
        assert ranks["B"] > ranks["C"]
        
        print("✅ Verification Passed!")
        
    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pagerank()
