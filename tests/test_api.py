import json
import unittest
from unittest.mock import patch, MagicMock
import os

from solr.importer.api import app


class TestImportEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        self.test_data = [
            {
                "id": 1,
                "gender": "Male",
                "age": 30,
                "name": "Test Document",
                "email": "test@test.com",
                "address": "123 Test St",
                "city": "New York",
                "state": "NY",
                "search_for": "Female",
            }
        ]

    @patch("solr.importer.api.get_solr_client")
    @patch.dict(os.environ, {"SOLR_URL": "http://localhost:8983/solr", "SOLR_COLLECTION": "test_collection"})
    def test_import_endpoint_success(self, mock_get_solr_client):
        mock_solr_client = MagicMock()
        mock_get_solr_client.return_value = mock_solr_client
        
        response = self.client.post(
            "/import",
            data=json.dumps(self.test_data),
            content_type="application/json",
        )

        mock_get_solr_client.assert_called_once_with("http://localhost:8983/solr", "test_collection")
        mock_solr_client.add.assert_called_once()
        mock_solr_client.commit.assert_called_once()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "OK"})

    @patch.dict(os.environ, {"SOLR_URL": "http://localhost:8983/solr", "SOLR_COLLECTION": "test_collection"})
    def test_import_endpoint_validation_error(self):
        invalid_test_data = [{"id": 1, "name": "Test Document"}]  # Missing required fields
        response = self.client.post(
            "/import",
            data=json.dumps(invalid_test_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Validation Error", json.loads(response.data)["error"])

    @patch("solr.importer.api.get_solr_client")
    @patch.dict(os.environ, {"SOLR_URL": "http://localhost:8983/solr", "SOLR_COLLECTION": "test_collection"})
    def test_import_endpoint_solr_error(self, mock_get_solr_client):
        # Test Solr connection errors
        mock_solr_client = MagicMock()
        mock_solr_client.add.side_effect = Exception("Solr connection failed")
        mock_get_solr_client.return_value = mock_solr_client
        
        response = self.client.post(
            "/import",
            data=json.dumps(self.test_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 500)
        self.assertIn("Solr connection failed", json.loads(response.data)["error"])


if __name__ == "__main__":
    unittest.main()