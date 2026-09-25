import pysolr

from solr.usage.document import get_solr_client
from solr.util import print_ascii_title, require_env


def query_solr_collection(client: pysolr.Solr) -> str:
    results = client.search("*:*", **{"q.op": "OR", "indent": "true", "useParams": ""})

    for result in results:
        print(result)

    return results


def query_solr_with_filter(client: pysolr.Solr, name: str) -> str:
    query = f'name:"{name}"'
    results = client.search(query, **{"q.op": "OR", "indent": "true", "useParams": ""})

    for result in results:
        print(result)

    return results


def query_document_count(client: pysolr.Solr) -> int:
    results = client.search("*:*", rows=0)
    return results.hits


def query_by_age_range(client: pysolr.Solr, min_age: int, max_age: int) -> list[str]:
    results = client.search(
        f"age:[{min_age} TO {max_age}]", **{"q.op": "AND", "indent": "true"}
    )

    return [str(result) for result in results]


def query_by_gender_and_city(client: pysolr.Solr, gender: str, city: str) -> list[str]:
    results = client.search(
        f"gender:{gender} AND city:{city}",
        **{"q.op": "AND", "indent": "true"},
    )

    return [str(result) for result in results]


def query_with_boosting(client: pysolr.Solr, search_term: str) -> list[str]:
    results = client.search(
        f"name:{search_term}^2 OR email:{search_term}",
        **{"q.op": "OR", "indent": "true"},
    )
    return [str(result) for result in results]


def main() -> None:
    solr_url, collection_name = require_env("SOLR_URL", "SOLR_COLLECTION")
    print_ascii_title("SOLR QUERY")

    solr_client = get_solr_client(solr_url, collection_name)

    print("Querying without filter...")
    query_solr_collection(solr_client)

    print("Querying with filter...")
    query_solr_with_filter(solr_client, "Robert Stevens")

    print("Querying document count...")
    document_count = query_document_count(solr_client)
    print(f"The collection {collection_name} has {document_count} documents.")


if __name__ == "__main__":
    main()
