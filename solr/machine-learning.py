import json
import os
from argparse import ArgumentParser, Namespace

from sentence_transformers import SentenceTransformer

from document import generate_documents, get_solr_client
from .util import with_env

SEMANTIC_WITH_PRETRAINED_MODEL = False
HYBRID_SEARCH_WITH_SOLR_LTR = False


def load_queries_from_json(file_path: str) -> dict:
    with open(file_path, "r") as file:
        queries = json.load(file)
    return queries


def index_document_with_embeddings(doc: dict, model: SentenceTransformer) -> dict:
    # Create a meaningful text representation from document fields
    fields = load_solr_fields()
    text_to_embedding = " ".join(
        [f"{doc.get(field, '')}" for field in fields if field in doc]
    )

    if not text_to_embedding.strip():
        text_to_embedding = "No text available for this document"

    # Generate vector embedding
    embedding = model.encode(text_to_embedding)
    doc["vector_field"] = embedding.tolist()
    return doc


def semantic_search(
    query: str, solr_url: str, model: SentenceTransformer, top_k: int = 100
) -> list:
    query_embedding = model.encode(query)

    vector_str = "[" + ",".join(str(x) for x in query_embedding.tolist()) + "]"

    # Use the proper KNN query syntax
    params = {
        "q": "*:*",
        "fq": f"{{!knn f=vector_field topK={top_k}}}{vector_str}",
        "fl": "*,score",
        "rows": top_k,
    }

    solr = get_solr_client(solr_url, "")
    results = solr.search(**params)

    print(
        f"Found {len(results.docs)} results with KNN search, lasted for {results.qtime}ms"
    )
    return results.docs


def load_solr_fields() -> list[str]:
    results = []
    with open("../json/fields.json", "r") as schema_file:
        schema = json.load(schema_file)
        for field in schema["add-field"]:
            results.append(field["name"])

    if results is None or len(results) == 0:
        raise Exception("No fields in fields.json defined")

    return results


def hybrid_search(
    query: str,
    solr_url: str,
    model: SentenceTransformer,
    text_weight: float = 0.5,
    vector_weight: float = 0.5,
    top_k: int = 100,
) -> list:
    query_embedding = model.encode(query)
    vector_str = "[" + ",".join(str(x) for x in query_embedding.tolist()) + "]"

    # Proper hybrid search parameters using fq for vector search
    params = {
        "q": query,  # Text search using standard query
        "fq": f"{{!knn f=vector_field topK={top_k}}}{vector_str}",  # Vector search as filter
        "fl": "*,score",
        "rows": top_k,
        "defType": "edismax",  # Use edismax for better text search
        "qf": "name address city email",  # Specify which fields to search in
    }

    solr = get_solr_client(solr_url, "")
    results = solr.search(**params)
    print(f"Found {len(results.docs)} results with hybrid search")

    return results.docs


@with_env(required_variables=["SOLR_URL", "SOLR_COLLECTION"])
def main() -> None:
    solr_url = os.getenv("SOLR_URL")
    collection_name = os.getenv("SOLR_COLLECTION")

    solr_url_with_collection = f"{solr_url}/{collection_name}"
    solr = get_solr_client(solr_url, collection_name)

    if SEMANTIC_WITH_PRETRAINED_MODEL:
        # Choosen ML-Models from https://huggingface.co/models
        # Good model for our dating app case: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
        model = SentenceTransformer("all-MiniLM-L6-v2")
        # This model needs a high performance GPU: https://huggingface.co/deepseek-ai/DeepSeek-R1/discussions & maybe is not the best choice for our case
        # (ML-Model catgory: Text-Gereration)
        # model = AutoModelForCausalLM.from_pretrained("deepseek-ai/DeepSeek-R1", trust_remote_code=True)

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

        # fyi: find similar documents based on this query sentence
        queries = load_queries_from_json("../json/sentences.json")
        sentences = queries["sentences"]
        query = sentences[0]["content"]
        results = semantic_search(query, solr_url_with_collection, model)
        print(
            "Sample documents with semantic search (vector based):",
            json.dumps(results, indent=2),
        )

    if HYBRID_SEARCH_WITH_SOLR_LTR:
        model = SentenceTransformer("all-MiniLM-L6-v2")

        # Generate and index documents if none exist
        response = solr.search("*:*", rows=1)
        if response.hits == 0:
            print("No documents found in index. Generating and indexing documents...")
            documents = generate_documents(0, 1000)
            documents_with_embeddings = [
                index_document_with_embeddings(doc, model) for doc in documents
            ]
            solr.add(documents_with_embeddings)
            solr.commit()
            print(f"Indexed {len(documents)} documents with embeddings")

        # Perform hybrid search
        query = "looking for someone who likes hiking and outdoor activities"
        results = hybrid_search(
            query=query,
            solr_url=solr_url_with_collection,
            model=model,
            text_weight=0.4,
            vector_weight=0.6,
            top_k=10,
        )

        print(f"Top results for query '{query}':")
        for i, doc in enumerate(results[:3], 1):
            print(f"{i}. {doc.get('title', 'No title')} - Score: {doc.get('score', 0)}")


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument(
        "--hybrid",
        action="store_true",
        help="Enable hybrid search with Solr LTR",
    )
    parser.add_argument(
        "--semantic",
        action="store_true",
        help="Enable semantic search with a pretrained model",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    HYBRID_SEARCH_WITH_SOLR_LTR = args.hybrid
    SEMANTIC_WITH_PRETRAINED_MODEL = args.semantic

    main()
