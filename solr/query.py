import os

from dotenv import load_dotenv

from solr.security import print_ascii_title
from solr.document import get_solr_client


solr = get_solr_client(os.getenv("SOLR_URL"), os.getenv("SOLR_COLLECTION"))

def main() -> None:
    load_dotenv()
    solr_url = os.getenv("SOLR_URL")
    collection_name = os.getenv("SOLR_COLLECTION")

    print_ascii_title("SOLR QUERY")

    print("Querying without filter...")
    query_solr_collection()

    print("Querying with filter...")
    query_solr_with_filter("Robert Stevens")

    print("Querying document count...")
    document_count = query_document_count()
    print(f"The collection {collection_name} has {document_count} documents.")


def query_solr_collection() -> str:
    results = solr.search("*:*", **{"q.op": "OR", "indent": "true", "useParams": ""})

    for result in results:
        print(result)

    return results


def query_solr_with_filter(name: str) -> str:
    query = f'name:"{name}"'
    results = solr.search(query, **{"q.op": "OR", "indent": "true", "useParams": ""})

    for result in results:
        print(result)

    return results


def query_document_count() -> int:
    results = solr.search("*:*", rows=0)
    return results.hits


def query_by_age_range(min_age: int, max_age: int) -> list[str]:
    results = solr.search(
        f"age:[{min_age} TO {max_age}]", **{"q.op": "AND", "indent": "true"}
    )

    return [str(result) for result in results]


def query_by_gender_and_city(gender: str, city: str) -> list[str]:
    results = solr.search(
        f"gender:{gender} AND city:{city}",
        **{"q.op": "AND"},
        **{
            "indent": "true",
            "q.op": "AND",
        },
    )

    return [str(result) for result in results]


def query_with_boosting(search_term: str) -> list[str]:
    results = solr.search(
        f"name:{search_term}^2 OR email:{search_term}",
        **{"q.op": "OR", "indent": "true"},
    )
    return [str(result) for result in results]


if __name__ == "__main__":
    main()
