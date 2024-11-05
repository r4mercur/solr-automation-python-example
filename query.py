import pysolr
import os
from dotenv import load_dotenv

def query_solr_collection():
    solr = pysolr.Solr(solr_url + "/" + collection_name, always_commit=True)
    results = solr.search('*:*', **{
        'q.op': 'OR',
        'indent': 'true',
        'useParams': ''
    })

    for result in results:
        print(result)


if __name__ == '__main__':
    # Load environment variables
    load_dotenv()

    # Solr server URL
    solr_url = os.getenv('SOLR_URL')
    # Collection name
    collection_name = os.getenv('SOLR_COLLECTION')

    query_solr_collection()