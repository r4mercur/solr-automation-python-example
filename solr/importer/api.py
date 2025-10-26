import json
import os

from flask import Flask, request
from flask_restx import Api, Resource, fields
from pydantic import ValidationError

from solr.usage.document import SolrImportPayload, SolrDocument, get_solr_client
from solr.util import with_env

app = Flask(__name__)
api = Api(app, version="1.0", description="Solr Import API", doc="/swagger/")

document_model = api.model(
    "SolrDocument",
    {
        "id": fields.String(required=True, description="Document ID"),
        "title": fields.String(required=True, description="Document Title"),
        "content": fields.String(required=True, description="Document Content"),
    },
)

import_payload = api.model(
    "ImportPayload", {"documents": fields.List(fields.Nested(document_model))}
)

response_model = api.model(
    "Response",
    {
        "status": fields.String(description="Status of the operation"),
        "error": fields.String(description="Error message if any"),
    },
)


@api.route("/import")
class ImportResource(Resource):
    @api.expect(import_payload)
    @api.response(200, "Success", response_model)
    @api.response(400, "Validation Error", response_model)
    @api.response(500, "Internal Server Error", response_model)
    def post(self):
        client = get_solr_client(os.getenv("SOLR_URL"), os.getenv("SOLR_COLLECTION"))

        try:
            raw_data = request.get_json()
            payload = validate_payload(raw_data)

            solr_documents = [doc.model_dump() for doc in payload.documents]
            json_data = json.dumps(solr_documents).encode("utf-8")

            client.add(json_data)
            client.commit()
            return {"status": "OK"}, 200

        except ValidationError as e:
            return {"error": f"Validation Error: {str(e)}"}, 400
        except Exception as e:
            return {"error": str(e)}, 500


def validate_payload(raw_data) -> SolrImportPayload:
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
