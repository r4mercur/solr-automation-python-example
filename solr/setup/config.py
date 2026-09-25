import logging

import requests

from solr.setup.schema import reload_solr_collection
from solr.util import HTTP_TIMEOUT, check_response, require_env, setup_logging

logger = logging.getLogger(__name__)


def configure_ltr_plugin(solr_url: str, collection_name: str) -> None:
    url = f"{solr_url}/{collection_name}/config"

    query_parser_config = {
        "add-queryparser": {
            "name": "ltr",
            "class": "org.apache.solr.ltr.search.LTRQParserPlugin",
        }
    }
    # Since Solr 10 (SOLR-16667) the transformer has no "fvCacheName" anymore. Feature vectors
    # are cached in the built-in <featureVectorCache>, which can only be enabled in
    # solrconfig.xml (not via the Config API); without it, features are just not cached.
    features_transformer_config = {
        "add-transformer": {
            "name": "features",
            "class": "org.apache.solr.ltr.response.transform.LTRFeatureLoggerTransformerFactory",
        }
    }

    for config in [query_parser_config, features_transformer_config]:
        response = requests.post(url, json=config, timeout=HTTP_TIMEOUT)
        # Solr rejects "add-*" for components that exist already, so re-runs are no error
        if response.status_code == 400 and "already exists" in response.text:
            logger.info("LTR config already exists, skipping: %s", config)
            continue
        check_response(response)
        logger.info("Configured LTR plugin successfully: %s", config)

    reload_solr_collection(solr_url, collection_name)


def main() -> None:
    setup_logging()
    solr_url, collection_name = require_env("SOLR_URL", "SOLR_COLLECTION")

    configure_ltr_plugin(solr_url, collection_name)


if __name__ == "__main__":
    main()
