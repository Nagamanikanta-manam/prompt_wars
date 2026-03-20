import unittest
import asyncio
from unittest.mock import patch, MagicMock
from harvest_link.agent import dispatch_driver

class TestAgentTools(unittest.IsolatedAsyncioTestCase):
    @patch('harvest_link.agent.db')
    @patch('harvest_link.agent.get_distance')
    async def test_find_best_charity(self, mock_get_distance, mock_db):
        from harvest_link.agent import find_best_charity
        import json
        
        # mock DB setup
        mock_charity1 = MagicMock()
        mock_charity1.to_dict.return_value = {"zip": "90211", "needs": ["vegetables"]}
        mock_charity2 = MagicMock()
        mock_charity2.to_dict.return_value = {"zip": "90212", "needs": ["any"]}
        
        mock_db.collection.return_value.stream.return_value = [mock_charity1, mock_charity2]
        
        mock_get_distance.side_effect = [10, 5] # dist for c1, c2
        
        res_json = await find_best_charity("vegetables")
        res = json.loads(res_json)
        
        # the best should be c2 because distance 5 < 10
        self.assertEqual(res["zip"], "90212")

    async def test_dispatch_driver(self):
        res = await dispatch_driver("Best Charity")
        self.assertEqual(res, "Driver dispatched to Best Charity")

    @patch('harvest_link.agent.upload_to_storage')
    async def test_generate_docs(self, mock_upload):
        from harvest_link.agent import generate_docs
        res = await generate_docs("Donor A", "Best Charity", '[{"name": "vegetables", "amount": 60}]')
        self.assertEqual(res, "Docs stored in GCS")
        mock_upload.assert_called_once()
        
    @patch('harvest_link.agent.store_request')
    async def test_process_donation(self, mock_store):
        from harvest_link.agent import process_donation
        res = await process_donation("Apples")
        self.assertEqual(res, "Stored")
        mock_store.assert_called_once()

if __name__ == "__main__":
    unittest.main()
