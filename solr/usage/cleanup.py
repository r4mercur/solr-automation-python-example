import os

from solr.usage.document import get_solr_client
from solr.util import with_env


def delete_all_documents(solr_url: str, collection_name: str) -> None:
    try:
        client = get_solr_client(solr_url, collection_name)
        client.delete(q="*:*")

        print(f"All Documents from collection '{collection_name}' were deleted.")

    except Exception as e:
        print(f"Error when trying to delete documents: {e}")


@with_env(required_variables=["SOLR_URL", "SOLR_COLLECTION"])
def main() -> None:
    solr_url = os.getenv("SOLR_URL")
    collection_name = os.getenv("SOLR_COLLECTION")

    print(f"Delete all documents from {solr_url}/{collection_name}...")
    delete_all_documents(solr_url, collection_name)


if __name__ == "__main__":
    main()
