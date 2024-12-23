import os

import requests
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    solr_url = os.getenv("SOLR_URL")
    collection_name = os.getenv("SOLR_COLLECTION")
    create_solr_collection(solr_url, collection_name)


def create_solr_collection(
        temp_solr_url: str, temp_collection_name: str, number_of_shards: int = 4, replication_factor: int = 2
) -> None:
    create_collection_url = f"{temp_solr_url}/admin/collections?action=CREATE&name={temp_collection_name}&numShards={number_of_shards}&replicationFactor={replication_factor}"
    response = requests.get(create_collection_url)
    if response.status_code == 200:
        print(f"Collection {temp_collection_name} created successfully.")
    else:
        print(f"Failed to create collection {temp_collection_name}: {response.text}")


if __name__ == "__main__":
    main()
