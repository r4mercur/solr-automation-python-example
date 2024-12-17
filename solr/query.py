import pysolr
import os
from dotenv import load_dotenv

def query_solr_collection() -> str:
    solr = pysolr.Solr(solr_url + "/" + collection_name, always_commit=True)
    results = solr.search('*:*', **{
        'q.op': 'OR',
        'indent': 'true',
        'useParams': ''
    })

    for result in results:
        print(result)

    return results

def query_solr_with_filter(name: str) -> str:
    solr = pysolr.Solr(solr_url + "/" + collection_name, always_commit=True)
    results = solr.search('name:' + name, **{
        'q.op': 'OR',
        'indent': 'true',
        'useParams': ''
    })

    for result in results:
        print(result)

    return results

def query_document_count(sorl_url: str, collection_name: str) -> int:
    solr = pysolr.Solr(solr_url + "/" + collection_name, always_commit=True)
    results = solr.search('*:*', rows=0)
    return results.hits


if __name__ == '__main__':
    # Load environment variables
    load_dotenv()

    # Solr server URL
    solr_url = os.getenv('SOLR_URL')
    # Collection name
    collection_name = os.getenv('SOLR_COLLECTION')

    print('Querying without filter...')
    query_solr_collection()

    print('Querying with filter...')
    query_solr_with_filter('John')

    print('Querying document count...')
    document_count = query_document_count(solr_url, collection_name)
    print(f'The collection {collection_name} has {document_count} documents.')