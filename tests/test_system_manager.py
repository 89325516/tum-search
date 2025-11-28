import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from system_manager import SystemManager, SPACE_X, SPACE_R

class TestSystemManager(unittest.TestCase):

    def setUp(self):
        self.mgr = SystemManager()

    @patch('system_manager.client')
    @patch('system_manager.get_embedding')
    def test_add_to_space_x(self, mock_get_embedding, mock_client):
        # Mock embedding
        mock_get_embedding.return_value = [0.1]*512
        
        self.mgr.add_to_space_x(text="hello world", url="http://test.com")
        
        mock_client.upsert.assert_called_once()
        call_args = mock_client.upsert.call_args
        self.assertEqual(call_args.kwargs['collection_name'], SPACE_X)
        
        # Verify payload
        points = call_args.kwargs['points']
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].payload['url'], "http://test.com")

    @patch('system_manager.client')
    def test_promote_from_x_to_r(self, mock_client):
        # Mock retrieve
        mock_point = MagicMock()
        mock_point.id = "test_id"
        mock_point.vector = [0.1]*512
        mock_point.payload = {"url": "http://test.com", "type": "text"}
        
        mock_client.retrieve.return_value = [mock_point]
        
        # Mock search in R (novelty check) - wait, promote_from_x_to_r doesn't check novelty, 
        # it's an admin force promote.
        # It calls trigger_global_recalculation which calls client.scroll
        
        # Mock scroll for trigger_global_recalculation
        mock_client.scroll.return_value = ([], None) # Empty R space to stop recursion
        
        success = self.mgr.promote_from_x_to_r("test_id")
        
        self.assertTrue(success)
        # Should upsert to SPACE_R
        mock_client.upsert.assert_called()
        # Check if any upsert call was for SPACE_R
        calls = mock_client.upsert.call_args_list
        r_calls = [c for c in calls if c.kwargs['collection_name'] == SPACE_R]
        self.assertTrue(len(r_calls) > 0)

    @patch('system_manager.client')
    @patch('system_manager.crawler')
    @patch('system_manager.get_embedding')
    def test_process_url_and_add(self, mock_get_embedding, mock_crawler, mock_client):
        # Mock crawler
        mock_crawler.parse.return_value = {
            'texts': ["Content 1", "Content 2"],
            'images': []
        }
        
        # Mock embedding
        mock_get_embedding.return_value = [0.1]*512
        
        # Mock novelty check. 
        # _check_novelty uses self.r_cache.
        # We can mock _check_novelty method on the instance since it is a method.
        with patch.object(self.mgr, '_check_novelty', return_value=(True, 1.0)):
            # Mock trigger_global_recalculation to avoid complex logic
            with patch.object(self.mgr, 'trigger_global_recalculation') as mock_trigger:
                self.mgr.process_url_and_add("http://test.com")
                
                # Should call upsert to SPACE_R (because novel)
                calls = mock_client.upsert.call_args_list
                r_calls = [c for c in calls if c.kwargs['collection_name'] == SPACE_R]
                self.assertTrue(len(r_calls) > 0)
                
                # Should also call upsert to SPACE_X
                x_calls = [c for c in calls if c.kwargs['collection_name'] == SPACE_X]
                self.assertTrue(len(x_calls) > 0)

if __name__ == '__main__':
    unittest.main()
