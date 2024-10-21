import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Solr server URL
solr_url = os.getenv('SOLR_URL')

# Collection name
collection_name = os.getenv('SOLR_COLLECTION')


def create_solr_collection(temp_solr_url: str, temp_collection_name: str) -> None:
    create_collection_url = f'{temp_solr_url}/admin/collections?action=CREATE&name={temp_collection_name}&numShards=1&replicationFactor=1&collection.configName=_default'
    response = requests.get(create_collection_url)
    if response.status_code == 200:
        print(f'Collection {temp_collection_name} created successfully.')
    else:
        print(f'Failed to create collection {temp_collection_name}: {response.text}')

# Create the collection
create_solr_collection(solr_url, collection_name)
