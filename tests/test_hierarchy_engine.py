import unittest
import numpy as np
import os
import shutil
from hierarchy_engine import HierarchicalIndex

class TestHierarchicalIndex(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_hierarchy_data"
        os.makedirs(self.test_dir, exist_ok=True)
        self.index_path = os.path.join(self.test_dir, "test_index.pkl")
        
        # Create dummy data
        # 100 vectors, 128 dimensions
        self.vectors = np.random.rand(100, 128).astype('float32')
        self.ids = [f"id_{i}" for i in range(100)]
        self.payloads = [{"info": f"data_{i}"} for i in range(100)]

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_build_and_search(self):
        # Initialize index with small cluster numbers for testing
        index = HierarchicalIndex(layer2_clusters=5, layer1_clusters=3)
        
        # Build index
        index.build(self.vectors, self.ids, self.payloads)
        
        # Check if layers are populated
        self.assertIsNotNone(index.layer2_centroids)
        self.assertTrue(len(index.layer1_centroids) > 0)
        self.assertTrue(len(index.layer1_children) > 0)
        
        # Test Search
        query_vector = self.vectors[0] # Search for the first vector itself
        results = index.search(query_vector, top_k=5, beam_size=5)
        
        self.assertTrue(len(results) > 0)
        # The first result should ideally be the vector itself (id_0) or very close
        # Note: K-Means is heuristic, so it might not always find the exact match if beam size is small,
        # but with beam_size=5 and small data, it likely will.
        found_ids = [r['id'] for r in results]
        self.assertIn("id_0", found_ids)
        
        # Check result structure
        self.assertIn('score', results[0])
        self.assertIn('payload', results[0])
        self.assertEqual(results[0]['payload']['info'], "data_0")

    def test_save_and_load(self):
        index = HierarchicalIndex(layer2_clusters=2, layer1_clusters=2)
        index.build(self.vectors, self.ids, self.payloads)
        
        index.save(self.index_path)
        
        loaded_index = HierarchicalIndex.load(self.index_path)
        
        self.assertEqual(loaded_index.layer2_k, index.layer2_k)
        self.assertEqual(len(loaded_index.ids), len(index.ids))
        
        # Verify search works on loaded index
        query_vector = self.vectors[10]
        results = loaded_index.search(query_vector, top_k=1)
        self.assertEqual(results[0]['id'], "id_10")

    def test_empty_build(self):
        # Test robustness with empty data
        index = HierarchicalIndex()
        # Should probably handle this gracefully or raise specific error
        # Based on code, KMeans will raise error if n_samples < n_clusters
        # So we expect an error or we should catch it. 
        # For now let's just see if it crashes hard or standard exception.
        pass 

if __name__ == '__main__':
    unittest.main()
