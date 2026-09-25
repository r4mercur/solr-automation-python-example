import logging
import os

from flask import Flask, request
from flask_restx import Api, Resource, fields

from solr.usage.document import SolrImportPayload, SolrDocument, get_solr_client
from solr.util import require_env, setup_logging

logger = logging.getLogger(__name__)

app = Flask(__name__)
api = Api(app, version="1.0", description="Solr Import API", doc="/swagger/")

document_model = api.model(
    "SolrDocument",
    {
        "id": fields.Integer(required=True, description="Document ID"),
        "gender": fields.String(required=True, example="Female"),
        "age": fields.Integer(required=True, min=18, max=80),
        "name": fields.String(required=True),
        "email": fields.String(required=True, example="jane.doe@example.com"),
        "address": fields.String(required=True),
        "city": fields.String(required=True),
        "state": fields.String(required=True),
        "search_for": fields.String(required=True, example="Male"),
    },
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
    # Accepts a list of documents (shown in Swagger) or a single document
    @api.expect([document_model])
    @api.response(200, "Success", response_model)
    @api.response(400, "Validation Error", response_model)
    @api.response(500, "Internal Server Error", response_model)
    def post(self):
        client = get_solr_client(os.getenv("SOLR_URL"), os.getenv("SOLR_COLLECTION"))

        try:
            # silent=True: invalid JSON returns None and ends up as a 400 below
            raw_data = request.get_json(silent=True)
            payload = validate_payload(raw_data)

            solr_documents = [doc.model_dump() for doc in payload.documents]

            client.add(solr_documents)
            client.commit()
            return {"status": "OK"}, 200

        except ValueError as e:  # includes pydantic's ValidationError
            return {"error": f"Validation Error: {str(e)}"}, 400
        except Exception as e:
            logger.exception("Import into Solr failed")
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


def main() -> None:
    setup_logging()
    require_env("SOLR_URL", "SOLR_COLLECTION")
    # Flask reads FLASK_DEBUG (e.g. from .env) itself, so debug mode is off by default
    app.run(port=5000)


if __name__ == "__main__":
    main()
