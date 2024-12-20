import os
import pysolr
import time
import numpy as np
from dotenv import load_dotenv
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from faker.proxy import Faker
from prometheus_client import Counter, Gauge, start_http_server
from pydantic import BaseModel, EmailStr, Field, ValidationError

class EmailValidator(BaseModel):
    email: EmailStr

class SolrDocument(BaseModel):
    id: int
    gender: str
    age: int = Field(..., ge=18, le=80)
    name: str
    email: EmailStr
    address: str
    city: str
    state: str
    search_for: str

    @staticmethod
    def cast_to_email_str(value: str) -> EmailStr:
        try:
            validated = EmailValidator.model_validate({'email': value})
            return validated.email
        except ValidationError as e:
            raise ValueError(f"Invalid email: {value}") from e

DOCUMENTS_PROCESSED = Counter('documents_processed', 'Number of documents processed', ['status'])
DOCUMENTS_ADDED = Counter('documents_added', 'Number of documents added', ['status'])
PROCESS_TIME = Gauge('process_time', 'Time taken to process documents')

def main() -> None:
    load_dotenv()
    solr_url = os.getenv('SOLR_URL')
    collection_name = os.getenv('SOLR_COLLECTION')
    # start monitoring
    start_http_server(8000)
    # note that should take around 2-3 minutes to run (5 million documents (7 minutes))
    create_documents(solr_url, collection_name, 100, 10)


def pre_generate_random_data(chunk_size: int) -> tuple:
    genders = np.random.choice(['Male', 'Female', 'Diverse'], size=chunk_size)
    ages = np.random.randint(18, 80, size=chunk_size)
    return genders, ages


def add_documents_to_solr(solr_clients: list, documents: list, batch_size: int = 10_000) -> None:
    num_clients = len(solr_clients)
    for index in range(0, len(documents), batch_size):
        client_index = (index // batch_size) % num_clients
        solr_clients[client_index].add(documents[index: index + batch_size])
        DOCUMENTS_ADDED.labels(status='added').inc(len(documents[index: index + batch_size]))
        print(f'Added documents {index} to {index + batch_size} to Solr using client {client_index}')


def generate_documents(start_index: int, chunk_size: int) -> list:
    fake = Faker()
    documents = []
    genders, ages = pre_generate_random_data(chunk_size)

    for index in range(chunk_size):
        id_ = index + start_index
        try:
            document = SolrDocument(
                id=id_,
                gender=str(genders[index]),
                age=int(ages[index]),
                name=fake.name(),
                email=SolrDocument.cast_to_email_str(fake.email()),
                address=fake.address(),
                city=fake.city(),
                state=fake.state(),
                search_for=str(genders[index])
            )
            documents.append(document.model_dump())
            DOCUMENTS_PROCESSED.labels(status='processed').inc()
            print(f'Generated document {id_}:{documents[-1]}')
        except ValidationError as e:
            print(f'Validation error for document {id_}: {e}')

    return documents


def get_solr_client(url: str, collection_name: str) -> pysolr.Solr:
    return pysolr.Solr(url + "/" + collection_name, always_commit=True)

def create_documents(temp_solr_url: str, temp_collection_name: str, number_of_documents: int, chunk_size: int) -> None:
    clients = [get_solr_client(temp_solr_url, temp_collection_name) for _ in range(10)]
    start_time = time.time()
    max_processes = os.cpu_count() or 16
    number_of_threads = 100

    with ProcessPoolExecutor(max_workers=max_processes) as process_executors, \
            ThreadPoolExecutor(max_workers=number_of_threads) as threads_executors:

        tasks = []
        futures = [
            process_executors.submit(generate_documents, index, chunk_size)
            for index in range(1, number_of_documents + 1, chunk_size)
        ]

        for future in as_completed(futures):
            documents = future.result()
            tasks.append(threads_executors.submit(add_documents_to_solr, clients,
                                                  documents, 10_000))

        for task in as_completed(tasks):
            task.result()

    end_time = time.time()
    PROCESS_TIME.set(end_time - start_time)
    print(f'Documents added successfully in {end_time - start_time} seconds.')


if __name__ == '__main__':
    main()
