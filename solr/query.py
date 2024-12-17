import pysolr
import os
from dotenv import load_dotenv

def main() -> None:
    load_dotenv()
    solr_url = os.getenv('SOLR_URL')
    collection_name = os.getenv('SOLR_COLLECTION')

    print('Querying without filter...')
    query_solr_collection(solr_url, collection_name)

    print('Querying with filter...')
    query_solr_with_filter(solr_url, collection_name, 'John')

    print('Querying document count...')
    document_count = query_document_count(solr_url, collection_name)
    print(f'The collection {collection_name} has {document_count} documents.')

def query_solr_collection(solr_url: str, collection_name: str) -> str:
    solr = pysolr.Solr(solr_url + "/" + collection_name, always_commit=True)
    results = solr.search('*:*', **{
        'q.op': 'OR',
        'indent': 'true',
        'useParams': ''
    })

    for result in results:
        print(result)

    return results

def query_solr_with_filter(solr_url:str, collection_name: str, name: str) -> str:
    solr = pysolr.Solr(solr_url + "/" + collection_name, always_commit=True)
    results = solr.search('name:' + name, **{
        'q.op': 'OR',
        'indent': 'true',
        'useParams': ''
    })

    for result in results:
        print(result)

    return results

def query_document_count(solr_url: str, collection_name: str) -> int:
    solr = pysolr.Solr(solr_url + "/" + collection_name, always_commit=True)
    results = solr.search('*:*', rows=0)
    return results.hits


if __name__ == '__main__':
    main()