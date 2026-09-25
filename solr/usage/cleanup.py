import logging

from solr.usage.document import get_solr_client
from solr.util import require_env, setup_logging

logger = logging.getLogger(__name__)


def delete_all_documents(solr_url: str, collection_name: str) -> None:
    client = get_solr_client(solr_url, collection_name)
    client.delete(q="*:*")

    logger.info("All documents from collection '%s' were deleted.", collection_name)


def main() -> None:
    setup_logging()
    solr_url, collection_name = require_env("SOLR_URL", "SOLR_COLLECTION")

    logger.info("Delete all documents from %s/%s...", solr_url, collection_name)
    delete_all_documents(solr_url, collection_name)


if __name__ == "__main__":
    main()
