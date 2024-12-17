import os
import pysolr
import time
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from faker.proxy import Faker


def main() -> None:
    load_dotenv()
    solr_url = os.getenv('SOLR_URL')
    collection_name = os.getenv('SOLR_COLLECTION')
    create_documents(solr_url, collection_name)

def add_documents_to_solr(solr: pysolr.Solr, documents: list) -> None:
    print(f'Adding {len(documents)} documents to Solr')
    solr.add(documents)

def generate_documents(start_index: int, end_index: int, fake: Faker) -> list:
    documents = []
    for index in range(start_index, end_index):
        documents.append({
            "id": index,
            "gender": fake.random_element(elements=('Male', 'Female', 'Diverse')),
            "age": fake.random_int(min=18, max=80),
            "name": fake.name(),
            "email": fake.email(),
            "address": fake.address(),
            "city": fake.city(),
            "state": fake.state(),
            "search-for": fake.random_element(elements=('Male', 'Female', 'Diverse')),
        })
        print(f'Generated document {index}:{documents[-1]}')

    return documents

def create_documents(temp_solr_url: str, temp_collection_name: str) -> None:
    solr = pysolr.Solr(temp_solr_url + "/" + temp_collection_name, always_commit=True)
    fake = Faker()

    start_time = time.time()
    chunk_size = 10000
    number_of_documents = 500000
    number_of_threads = 10
    documents = []

    with ThreadPoolExecutor(max_workers=number_of_threads) as executor:
        futures = [executor.submit(generate_documents, index, index + chunk_size, fake)
                   for index in range(1, number_of_documents + 1, chunk_size)]
        for future in as_completed(futures):
            documents.extend(future.result())


    with ThreadPoolExecutor() as executor:
        for index in range(0, len(documents), chunk_size):
            chunk = documents[index:index + chunk_size]
            executor.submit(add_documents_to_solr, solr, chunk)

    end_time = time.time()
    print(f'Documents added successfully in {end_time - start_time} seconds.')


if __name__ == '__main__':
    main()