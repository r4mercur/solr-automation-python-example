import json
import unittest
from unittest.mock import patch

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

    @patch("solr.importer.api.solr.add")
    @patch("solr.importer.api.solr.commit")
    def test_import_endpoint_success(self, mock_commit, mock_add):
        response = self.client.post(
            "/import",
            data=json.dumps(self.test_data),
            content_type="application/json",
        )

        json_bytes = json.dumps(self.test_data).encode("utf-8")
        mock_add.assert_called_once_with(json_bytes)
        mock_commit.assert_called_once()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "OK"})

    def test_import_endpoint_validation_error(self):
        invalid_test_data = [{"id": 1, "name": "Test Document"}]
        response = self.client.post(
            "/import",
            data=json.dumps(invalid_test_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Validation Error", json.loads(response.data)["error"])
