import json
import os

from flask import Flask, request, jsonify
from pydantic import ValidationError

from solr.document import SolrImportPayload, SolrDocument, get_solr_client
from solr.util import with_env

app = Flask(__name__)

@app.route("/import", methods=["POST"])
def import_user():
    client = get_solr_client(os.getenv("SOLR_URL"), os.getenv("SOLR_COLLECTION"))
    
    try:
        raw_data = request.get_json()
        payload = validate_payload(raw_data)

        solr_documents = [doc.model_dump() for doc in payload.documents]
        json_data = json.dumps(solr_documents).encode("utf-8")

        client.add(json_data)
        client.commit()
        return jsonify({"status": "OK"}), 200

    except ValidationError as e:
        return jsonify({"error": f"Validation Error: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def validate_payload(raw_data):
    if isinstance(raw_data, list):
        payload = SolrImportPayload(documents=raw_data)
    elif isinstance(raw_data, dict):
        document = SolrDocument(**raw_data)
        payload = SolrImportPayload(documents=[document])
    else:
        raise ValueError("Data must be a list or a dictionary")
    return payload


@with_env(required_variables=["SOLR_URL", "SOLR_COLLECTION"])
def main():
    app.run(port=5000, debug=True)


if __name__ == "__main__":
    main()
