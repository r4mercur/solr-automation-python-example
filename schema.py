import os
import requests
import json

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Solr server URL
solr_url = os.getenv('SOLR_URL')
# Collection name
collection_name = os.getenv('SOLR_COLLECTION')


def update_solr_schema(temp_solr_url: str, temp_collection_name: str, temp_schema: dict) -> None:
    schema_url = f'{temp_solr_url}/{temp_collection_name}/schema'
    response = requests.post(schema_url, json=temp_schema)
    if response.status_code == 200:
        print('Schema updated successfully.')
    else:
        print(f'Failed to update schema: {response.text}')

def reload_solr_collection(temp_solr_url: str, temp_collection_name: str) -> None:
    reload_url = f'{temp_solr_url}/admin/collections?action=RELOAD&name={temp_collection_name}'
    response = requests.get(reload_url)
    if response.status_code == 200:
        print(f'Collection {temp_collection_name} reloaded successfully.')
    else:
        print(f'Failed to reload collection {temp_collection_name}: {response.text}')


schema_file_path = os.path.join(os.path.dirname(__file__), 'fields.json')
with open(schema_file_path, 'r') as schema_file:
    schema = json.load(schema_file)


update_solr_schema(solr_url, collection_name, schema)

reload_solr_collection(solr_url, collection_name)