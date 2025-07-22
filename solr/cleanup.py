import os

from dotenv import load_dotenv

from document import get_solr_client


def delete_all_documents(solr_url: str, collection_name: str) -> None:
    try:
        client = get_solr_client(solr_url, collection_name)
        client.delete(q="*:*")

        print(f"All Documents from collection '{collection_name}' were deleted.")

    except Exception as e:
        print(f"Error when trying to delete documents: {e}")


def main() -> None:
    load_dotenv()

    solr_url = os.getenv("SOLR_URL")
    collection_name = os.getenv("SOLR_COLLECTION")

    print(f"Delete all documents from {solr_url}/{collection_name}...")
    delete_all_documents(solr_url, collection_name)


if __name__ == "__main__":
    main()
