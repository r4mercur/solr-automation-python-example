import pysolr
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Solr server URL
solr_url = os.getenv('SOLR_URL')
collection_name = os.getenv('SOLR_COLLECTION')

def query_solr_collection():
    solr = pysolr.Solr(solr_url + "/" + collection_name, always_commit=True)
    results = solr.search('*:*', **{
        'q.op': 'OR',
        'indent': 'true',
        'useParams': ''
    })

    for result in results:
        print(result)

query_solr_collection()