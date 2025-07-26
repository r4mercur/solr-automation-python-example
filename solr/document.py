import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import List

import numpy as np
import pysolr
from .util import with_env
from faker.proxy import Faker
from prometheus_client import Counter, Gauge, start_http_server, REGISTRY
from pydantic import BaseModel, EmailStr, Field, ValidationError

_client_counter = threading.Lock()
_current_client_index = 0
turn_on_document_print = False


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

    class Config:
        extra = "allow"  # Allow extra fields in the input data

    @staticmethod
    def cast_to_email_str(value: str) -> EmailStr:
        try:
            validated = EmailValidator.model_validate({"email": value})
            return validated.email
        except ValidationError as e:
            raise ValueError(f"Invalid email: {value}") from e


class SolrImportPayload(BaseModel):
    documents: List[SolrDocument]


# Check if the metrics are already registered
if "documents_processed" not in REGISTRY._names_to_collectors:
    DOCUMENTS_PROCESSED = Counter(
        "documents_processed", "Number of documents processed", ["status"]
    )
if "documents_added" not in REGISTRY._names_to_collectors:
    DOCUMENTS_ADDED = Counter(
        "documents_added", "Number of documents added", ["status"]
    )
if "process_time" not in REGISTRY._names_to_collectors:
    PROCESS_TIME = Gauge("process_time", "Time taken to process documents")


"""
 Here methods to create Solr documents, add them to Solr, and manage Solr clients.
"""

def get_next_client_index(num_clients: int) -> int:
    global _current_client_index
    with _client_counter:
        index = _current_client_index
        _current_client_index = (_current_client_index + 1) % num_clients
        return index


def pre_generate_random_data(chunk_size: int) -> tuple:
    genders = np.random.choice(["Male", "Female", "Diverse"], size=chunk_size)
    ages = np.random.randint(18, 80, size=chunk_size)
    return genders, ages


def add_documents_to_solr(
    solr_clients: list, documents: list, start_doc_id: int, batch_size: int = 10_000
) -> None:
    num_clients = len(solr_clients)

    for index in range(0, len(documents), batch_size):
        client_index = get_next_client_index(num_clients)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                solr_clients[client_index].add(documents[index : index + batch_size])
                DOCUMENTS_ADDED.labels(status="added").inc(
                    len(documents[index : index + batch_size])
                )
                break
            except (pysolr.SolrError, ConnectionError) as e:
                if attempt == max_retries - 1:  # Letzter Versuch
                    print(f"Failed to add documents after {max_retries} attempts: {e}")
                    raise
                else:
                    print(f"Timeout attempt {attempt + 1}, retrying...")
                    time.sleep(2**attempt)

        global_start = start_doc_id + index
        global_end = start_doc_id + min(index + batch_size, len(documents))
        print(
            f"Added documents {global_start} to {global_end} to Solr using client {client_index}"
        )


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
                search_for=str(genders[index]),
            )
            documents.append(document.model_dump())
            DOCUMENTS_PROCESSED.labels(status="processed").inc()

            if turn_on_document_print:
                print(f"Generated document {id_}:{documents[-1]}")
        except ValidationError as e:
            print(f"Validation error for document {id_}: {e}")

    return documents


def get_solr_client(url: str, collection_name: str) -> pysolr.Solr:
    return pysolr.Solr(url + "/" + collection_name, always_commit=True, timeout=300)


def create_documents(
    temp_solr_url: str,
    temp_collection_name: str,
    number_of_documents: int,
    chunk_size: int,
) -> None:
    clients = [get_solr_client(temp_solr_url, temp_collection_name) for _ in range(10)]
    start_time = time.time()
    max_processes = os.cpu_count() or 16
    number_of_threads = 100

    with ProcessPoolExecutor(
        max_workers=max_processes
    ) as process_executors, ThreadPoolExecutor(
        max_workers=number_of_threads
    ) as threads_executors:

        tasks = []
        futures = []
        futures_to_start_index = {}
        for index in range(1, number_of_documents + 1, chunk_size):
            future = process_executors.submit(generate_documents, index, chunk_size)
            futures_to_start_index[future] = index
            futures.append(future)

        for future in as_completed(futures):
            documents = future.result()
            start_doc_id = futures_to_start_index[future]
            tasks.append(
                threads_executors.submit(
                    add_documents_to_solr, clients, documents, start_doc_id, 25_000
                )
            )

        for task in as_completed(tasks):
            task.result()

    end_time = time.time()
    PROCESS_TIME.set(end_time - start_time)
    print(f"Documents added successfully in {end_time - start_time} seconds.")


@with_env(required_variables=["SOLR_URL", "SOLR_COLLECTION"])
def main() -> None:
    solr_url = os.getenv("SOLR_URL")
    collection_name = os.getenv("SOLR_COLLECTION")
    # start monitoring
    start_http_server(8000)
    create_documents(solr_url, collection_name, 1000000, 5000)


if __name__ == "__main__":
    main()
