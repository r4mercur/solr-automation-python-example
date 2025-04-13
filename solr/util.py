import os

import pysolr
from dotenv import load_dotenv


def get_solr_client() -> pysolr.Solr:
    load_dotenv()
    solr_url = os.getenv("SOLR_URL")
    collection_name = os.getenv("SOLR_COLLECTION")
    return pysolr.Solr(f"{solr_url}/{collection_name}", always_commit=True)
