import os

import requests

from solr.setup.schema import reload_solr_collection
from solr.util import with_env


def configure_ltr_plugin(solr_url: str, collection_name: str) -> None:
    url = f"{solr_url}/{collection_name}/config"

    query_parser_config = {
        "add-queryparser": {
            "name": "ltr",
            "class": "org.apache.solr.ltr.search.LTRQParserPlugin",
        }
    }
    cache_config = {
        "add-cache": {
            "name": "QUERY_DOC_FV",
            "class": "solr.search.CaffeineCache",
            "size": 4096,
            "initialSize": 2048,
            "autowarmCount": 4096,
            "regenerator": "solr.search.NoOpRegenerator",
        }
    }
    features_transformer_config = {
        "add-transformer": {
            "name": "features",
            "class": "org.apache.solr.ltr.response.transform.LTRFeatureLoggerTransformerFactory",
            "fvCacheName": "QUERY_DOC_FV",
        }
    }

    for config in [query_parser_config, cache_config, features_transformer_config]:
        response = requests.post(url, json=config)
        if response.status_code == 200:
            print(f"Configured LTR plugin successfully: {config}")
        else:
            print(f"Failed to configure LTR plugin: {response.status_code}")

    reload_solr_collection(solr_url, collection_name)


@with_env(required_variables=["SOLR_URL", "SOLR_COLLECTION"])
def main() -> None:
    solr_url = os.getenv("SOLR_URL")
    collection_name = os.getenv("SOLR_COLLECTION")

    configure_ltr_plugin(solr_url, collection_name)


if __name__ == "__main__":
    main()
