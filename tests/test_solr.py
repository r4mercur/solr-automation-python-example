import unittest
import requests
import json
import os
import time
from dotenv import load_dotenv
from testcontainers.compose import DockerCompose

class TestSolrIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.compose = DockerCompose(os.path.dirname(__file__))
        cls.compose.start()

        # wait seconds for all services to start
        time.sleep(10)

        load_dotenv()
        cls.solr_url = 'http://localhost:8983/solr'
        cls.collection_name = 'test_collection'

        cls.wait_for_solr(cls.solr_url)

        cls.create_solr_collection(cls.solr_url, cls.collection_name)

    @classmethod
    def tearDownClass(cls):
        cls.delete_solr_collection(cls.solr_url, cls.collection_name)
        cls.compose.stop()

    @staticmethod
    def wait_for_solr(solr_url, timeout=60):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f'{solr_url}/admin/cores')
                if response.status_code == 200:
                    return
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1)
        raise Exception('Solr did not start within the timeout period')

    @staticmethod
    def create_solr_collection(solr_url, collection_name):
        create_collection_url = f'{solr_url}/admin/collections?action=CREATE&name={collection_name}&numShards=1&replicationFactor=1&collection.configName=_default'
        response = requests.get(create_collection_url)
        if response.status_code != 200:
            raise Exception(f'Failed to create collection {collection_name}: {response.text}')

    @staticmethod
    def delete_solr_collection(solr_url, collection_name):
        delete_collection_url = f'{solr_url}/admin/collections?action=DELETE&name={collection_name}'
        response = requests.get(delete_collection_url)
        if response.status_code != 200:
            raise Exception(f'Failed to delete collection {collection_name}: {response.text}')

    def test_update_solr_schema(self):
        schema_file_path = os.path.join(os.path.dirname(__file__), '../json/fields.json')
        with open(schema_file_path, 'r') as schema_file:
            schema = json.load(schema_file)

        schema_url = f'{self.solr_url}/{self.collection_name}/schema'
        response = requests.post(schema_url, json=schema)
        self.assertEqual(response.status_code, 200, f'Failed to update schema: {response.text}')

    def test_create_solr_collection(self):
        # Check if the collection exists
        status_url = f'{self.solr_url}/admin/collections?action=LIST'
        response = requests.get(status_url)
        self.assertEqual(response.status_code, 200, f'Failed to list collections: {response.text}')
        collections = response.json().get('collections', [])
        self.assertIn(self.collection_name, collections, f'Collection {self.collection_name} was not created.')

if __name__ == '__main__':
    unittest.main()