import json
import os
import time
import unittest

import requests
from testcontainers.compose import DockerCompose

from solr.setup.core import create_solr_collection
from solr.setup.schema import update_solr_schema, reload_solr_collection
from solr.usage.document import create_documents
from solr.util import with_env


class TestImplementationSolr(unittest.TestCase):
    @classmethod
    @with_env(required_variables=["SOLR_URL", "SOLR_COLLECTION"])
    def setUpClass(cls):
        cls.compose = DockerCompose(
            os.path.dirname(__file__), compose_file_name="docker-compose.test.yml"
        )
        cls.compose.start()

        cls.solr_url = os.getenv("SOLR_URL")
        cls.collection_name = os.getenv("SOLR_COLLECTION")
        cls.wait_for_solr_and_init_core(cls.solr_url, cls.collection_name)

    @classmethod
    def tearDownClass(cls):
        cls.compose.stop()

    @staticmethod
    def wait_for_solr_and_init_core(
        solr_url: str, collection_name: str, timeout: int = 60
    ):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{solr_url}/admin/cores")
                if response.status_code == 200:
                    # Init the solr collection
                    create_solr_collection(solr_url, collection_name)
                    return
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1)
        raise Exception("Solr did not start within the timeout period")

    def test_solr_core_implementation(self):
        core_status_url = (
            f"{self.solr_url}/admin/cores?action=STATUS&core={self.collection_name}"
        )
        response = requests.get(core_status_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.collection_name, response.json()["status"])

    def test_solr_schema_implementation(self):
        schema_file_path = os.path.join(
            os.path.dirname(__file__), "../json/fields.json"
        )
        with open(schema_file_path, "r") as schema_file:
            schema = json.load(schema_file)

        update_solr_schema(self.solr_url, self.collection_name, schema)
        reload_solr_collection(self.solr_url, self.collection_name)

        schema_url = f"{self.solr_url}/{self.collection_name}/schema"
        response = requests.get(schema_url)
        self.assertEqual(response.status_code, 200)

        fields_in_schema = [
            field["name"] for field in response.json()["schema"]["fields"]
        ]
        for field in schema["add-field"]:
            self.assertIn(field["name"], fields_in_schema)

    def test_documents_solr_implementation(self):
        schema_file_path = os.path.join(
            os.path.dirname(__file__), "../json/fields.json"
        )
        with open(schema_file_path, "r") as schema_file:
            schema = json.load(schema_file)

        update_solr_schema(self.solr_url, self.collection_name, schema)
        reload_solr_collection(self.solr_url, self.collection_name)
        create_documents(self.solr_url, self.collection_name, 100, 10)

        query_url = f"{self.solr_url}/{self.collection_name}/select"
        response = requests.get(query_url, params={"q": "*:*"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"]["numFound"], 100)
        self.assertEqual(len(response.json()["response"]["docs"]), 10)
