import logging

import requests

from solr.util import HTTP_TIMEOUT, check_response, require_env, setup_logging

logger = logging.getLogger(__name__)


def collection_exists(solr_url: str, collection_name: str) -> bool:
    response = requests.get(
        f"{solr_url}/admin/collections",
        params={"action": "LIST"},
        timeout=HTTP_TIMEOUT,
    )
    check_response(response)
    return collection_name in response.json().get("collections", [])


def create_solr_collection(
        solr_url: str,
        collection_name: str,
    number_of_shards: int = 4,
    replication_factor: int = 2,
) -> None:
    if collection_exists(solr_url, collection_name):
        logger.info("Collection %s already exists, skipping creation.", collection_name)
        return

    response = requests.get(
        f"{solr_url}/admin/collections",
        params={
            "action": "CREATE",
            "name": collection_name,
            "numShards": number_of_shards,
            "replicationFactor": replication_factor,
        },
        timeout=HTTP_TIMEOUT,
    )
    check_response(response)
    logger.info("Collection %s created successfully.", collection_name)


def main() -> None:
    setup_logging()
    solr_url, collection_name = require_env("SOLR_URL", "SOLR_COLLECTION")
    create_solr_collection(solr_url, collection_name)


if __name__ == "__main__":
    main()
