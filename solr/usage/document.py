import logging
import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import List

import numpy as np
import pysolr
from faker.proxy import Faker
from prometheus_client import Counter, Gauge, start_http_server
from pydantic import BaseModel, EmailStr, Field, ValidationError, ConfigDict

from solr.util import get_or_create_metric, require_env, setup_logging

logger = logging.getLogger(__name__)

_client_counter = threading.Lock()
_current_client_index = 0

# Define Prometheus metrics
DOCUMENTS_PROCESSED = get_or_create_metric(
    "documents_processed", Counter, "Number of documents processed", ["status"]
)
DOCUMENTS_ADDED = get_or_create_metric(
    "documents_added", Counter, "Number of documents added", ["status"]
)
PROCESS_TIME = get_or_create_metric(
    "process_time", Gauge, "Time taken to process documents"
)


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
    model_config = ConfigDict(extra="allow")

    @staticmethod
    def cast_to_email_str(value: str) -> EmailStr:
        try:
            validated = EmailValidator.model_validate({"email": value})
            return validated.email
        except ValidationError as e:
            raise ValueError(f"Invalid email: {value}") from e


class SolrImportPayload(BaseModel):
    documents: List[SolrDocument]


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
                    logger.error(
                        "Failed to add documents after %d attempts: %s", max_retries, e
                    )
                    raise
                else:
                    logger.warning(
                        "Attempt %d failed (%s), retrying...", attempt + 1, e
                    )
                    time.sleep(2**attempt)

        global_start = start_doc_id + index
        global_end = start_doc_id + min(index + batch_size, len(documents))
        logger.info(
            "Added documents %d to %d to Solr using client %d",
            global_start,
            global_end,
            client_index,
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

            logger.debug("Generated document %d: %s", id_, documents[-1])
        except ValidationError as e:
            logger.warning("Validation error for document %d: %s", id_, e)

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

    # initializer: worker processes don't inherit the logging config on Windows (spawn)
    with ProcessPoolExecutor(
            max_workers=max_processes, initializer=setup_logging
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
            # Count in the main process: metrics incremented inside the worker
            # processes never reach the Prometheus HTTP server started here
            DOCUMENTS_PROCESSED.labels(status="processed").inc(len(documents))
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
    logger.info(
        "Documents added successfully in %.2f seconds.", end_time - start_time
    )


def main() -> None:
    setup_logging()
    solr_url, collection_name = require_env("SOLR_URL", "SOLR_COLLECTION")
    # start monitoring
    start_http_server(8000)
    create_documents(solr_url, collection_name, 1000000, 5000)


if __name__ == "__main__":
    main()
