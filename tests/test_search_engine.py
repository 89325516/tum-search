import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import sys
import os

# Adjust path to import modules from parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from search_engine import gauss_rank_norm, search

class TestSearchEngine(unittest.TestCase):

    def test_gauss_rank_norm(self):
        scores = [0.1, 0.5, 0.9]
        norm_scores = gauss_rank_norm(scores)
        # Rank data: 1, 2, 3 -> divided by 3 -> 0.33, 0.66, 1.0
        self.assertAlmostEqual(norm_scores[0], 1/3)
        self.assertAlmostEqual(norm_scores[1], 2/3)
        self.assertAlmostEqual(norm_scores[2], 1.0)
        
        # Test empty
        self.assertEqual(gauss_rank_norm([]), [])

    @patch('search_engine.client')
    @patch('search_engine.clip_model')
    @patch('search_engine.clip_processor')
    @patch('search_engine.consistency_engine')
    def test_search(self, mock_consistency, mock_processor, mock_model, mock_client):
        # Mock CLIP
        mock_processor.return_value = {'input_ids': 'fake'}
        
        mock_features = MagicMock()
        # Return a tensor that supports .norm() and .numpy()
        mock_tensor = MagicMock()
        mock_tensor.norm.return_value = 1.0
        mock_tensor.__truediv__.return_value = mock_tensor
        mock_tensor.__getitem__.return_value = mock_tensor
        mock_tensor.numpy.return_value = np.array([[0.1, 0.2]])
        mock_tensor.tolist.return_value = [0.1, 0.2]
        
        mock_model.get_text_features.return_value = mock_tensor

        # Mock Qdrant Search
        mock_hit = MagicMock()
        mock_hit.id = "test_id_1"
        mock_hit.score = 0.9
        mock_hit.payload = {
            "pr_score": 0.5,
            "type": "text",
            "url": "http://example.com",
            "content_preview": "Test Content"
        }
        mock_client.search.return_value = [mock_hit]

        # Mock Consistency Engine
        mock_consistency.check_consistency.return_value = (True, 0.1)

        # Run Search
        results = search("test query", top_k=5)

        # Assertions
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['id'], "test_id_1")
        self.assertEqual(results[0]['url'], "http://example.com")
        
        # Verify calls
        mock_client.search.assert_called_once()
        mock_consistency.check_consistency.assert_called_once()

    @patch('search_engine.client')
    @patch('search_engine.clip_model')
    @patch('search_engine.clip_processor')
    @patch('search_engine.consistency_engine')
    def test_search_consistency_failure(self, mock_consistency, mock_processor, mock_model, mock_client):
        # Mock CLIP (same as above)
        mock_processor.return_value = {'input_ids': 'fake'}
        mock_tensor = MagicMock()
        mock_tensor.norm.return_value = 1.0
        mock_tensor.__truediv__.return_value = mock_tensor
        mock_tensor.__getitem__.return_value = mock_tensor
        mock_tensor.numpy.return_value = np.array([[0.1, 0.2]])
        mock_tensor.tolist.return_value = [0.1, 0.2]
        mock_model.get_text_features.return_value = mock_tensor

        # Mock Qdrant Search
        mock_hit = MagicMock()
        mock_hit.id = "test_id_blocked"
        mock_hit.score = 0.9
        mock_hit.payload = {}
        mock_client.search.return_value = [mock_hit]

        # Mock Consistency Engine to FAIL
        mock_consistency.check_consistency.return_value = (False, 10.0)

        # Run Search
        results = search("test query", top_k=5)

        # Should be empty because the only result was blocked
        self.assertEqual(len(results), 0)

if __name__ == '__main__':
    unittest.main()
