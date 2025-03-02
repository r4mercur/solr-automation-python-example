import json
import os

import pysolr
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from document import generate_documents


def main() -> None:
    load_dotenv()
    solr_url = os.getenv("SOLR_URL")
    collection_name = os.getenv("SOLR_COLLECTION")

    solr_url_with_collection = f"{solr_url}/{collection_name}"
    solr = pysolr.Solr(solr_url_with_collection)

    model = SentenceTransformer("all-MiniLM-L6-v2")

    documents = generate_documents(0, 1000)
    documents_with_embeddings = [
        index_document_with_embeddings(doc, model) for doc in documents
    ]

    solr.add(documents_with_embeddings)
    solr.commit()

    response = solr.search("*:*", rows=5)
    print(f"Total documents in Solr: {response.hits}")
    print(
        "Sample document:",
        json.dumps(
            response.docs[0] if response.docs else "No documents found", indent=2
        ),
    )

    query = "What is the capital of France?"
    results = semantic_search(query, solr_url_with_collection, model)
    print(results)


def index_document_with_embeddings(doc: dict, model: SentenceTransformer) -> dict:
    text_to_embedding = f"{doc['name']} {doc['email']} {doc['address']} {doc['city']} {doc['state']} {doc['search_for']}"
    embedding = model.encode(text_to_embedding)
    doc["vector_field"] = embedding.tolist()
    return doc


def semantic_search(
    query: str, solr_url: str, model: SentenceTransformer, top_k: int = 100
) -> list:
    query_embedding = model.encode(query)

    # Create vector string
    vector_str = "[" + ",".join(str(x) for x in query_embedding.tolist()) + "]"

    # Build query parameters using standard q parameter
    params = {"q": f"{{!knn f=vector_field topK={top_k}}}{vector_str}", "fl": "*,score"}

    solr = pysolr.Solr(solr_url)
    results = solr.search(**params)

    print(f"Found {len(results.docs)} results with KNN search")
    return results.docs


if __name__ == "__main__":
    main()
