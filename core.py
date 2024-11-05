import os
import requests
import pysolr
import json
from dotenv import load_dotenv


def create_solr_collection(temp_solr_url: str, temp_collection_name: str) -> None:
    create_collection_url = f'{temp_solr_url}/admin/collections?action=CREATE&name={temp_collection_name}&numShards=1&replicationFactor=1&collection.configName=_default'
    response = requests.get(create_collection_url)
    if response.status_code == 200:
        print(f'Collection {temp_collection_name} created successfully.')
    else:
        print(f'Failed to create collection {temp_collection_name}: {response.text}')

def create_documents(temp_solr_url: str, temp_collection_name: str) -> None:
    solr = pysolr.Solr(temp_solr_url + "/" + temp_collection_name,
                       always_commit=True)
    documents = json.load(open('documents.json'))
    solr.add(documents)
    print('Documents added successfully.')


if __name__ == '__main__':
    # Load environment variables
    load_dotenv()

    # Solr server URL
    solr_url = os.getenv('SOLR_URL')
    # Collection name
    collection_name = os.getenv('SOLR_COLLECTION')

    # Create the collection
    create_solr_collection(solr_url, collection_name)

    # Create example documents
    create_documents(solr_url, collection_name)