import logging

import requests

from solr.util import (
    HTTP_TIMEOUT,
    check_response,
    load_json,
    require_env,
    setup_logging,
)

logger = logging.getLogger(__name__)


def update_solr_schema(solr_url: str, collection_name: str, schema: dict) -> None:
    schema_url = f"{solr_url}/{collection_name}/schema"
    response = check_response(requests.get(schema_url, timeout=HTTP_TIMEOUT))

    current_schema = response.json().get("schema", {})

    current_version = current_schema.get("version", 1.0)
    existing_fields = {field["name"] for field in current_schema.get("fields", [])}
    existing_field_types = {
        field["name"] for field in current_schema.get("fieldTypes", [])
    }
    existing_dynamic_fields = {
        field["name"] for field in current_schema.get("dynamicFields", [])
    }

    json_fields = {field["name"] for field in schema.get("add-field", [])}
    json_delete_fields = {field["name"] for field in schema.get("delete-field", [])}

    new_field_types = [
        ft
        for ft in schema.get("add-field-type", [])
        if ft["name"] not in existing_field_types
    ]

    new_fields = [
        field
        for field in schema.get("add-field", [])
        if field["name"] not in existing_fields
    ]

    new_dynamic_fields = [
        field
        for field in schema.get("add-dynamic-field", [])
        if field["name"] not in existing_dynamic_fields
    ]

    necessary_fields = {"id", "_text_", "_nest_path_", "_root_", "_version_"}
    # Remove fields that are no longer in the json or explicitly marked for deletion
    # (a set, so a field matching both conditions is only deleted once)
    fields_to_remove = {
        field
        for field in existing_fields
        if (field not in json_fields or field in json_delete_fields)
           and field not in necessary_fields
    }

    update_payload = {}

    if new_field_types:
        update_payload["add-field-type"] = new_field_types

    if new_fields:
        update_payload["add-field"] = new_fields

    if new_dynamic_fields:
        update_payload["add-dynamic-field"] = new_dynamic_fields

    if fields_to_remove:
        update_payload["delete-field"] = [
            {"name": field} for field in sorted(fields_to_remove)
        ]

    if not update_payload:
        logger.info("No changes to the schema with version: %s", current_version)
        return

    logger.info("Updating schema: %s", update_payload)
    check_response(requests.post(schema_url, json=update_payload, timeout=HTTP_TIMEOUT))
    logger.info("Schema updated successfully.")

    check_response(
        requests.get(
            f"{solr_url}/{collection_name}/update",
            params={"commit": "true"},
            timeout=HTTP_TIMEOUT,
        )
    )
    logger.info("Changes committed successfully.")


def reload_solr_collection(solr_url: str, collection_name: str) -> None:
    response = requests.get(
        f"{solr_url}/admin/collections",
        params={"action": "RELOAD", "name": collection_name},
        timeout=HTTP_TIMEOUT,
    )
    check_response(response)
    logger.info("Collection %s reloaded successfully.", collection_name)


def main() -> None:
    setup_logging()
    solr_url, collection_name = require_env("SOLR_URL", "SOLR_COLLECTION")

    update_solr_schema(solr_url, collection_name, load_json("fields.json"))
    reload_solr_collection(solr_url, collection_name)


if __name__ == "__main__":
    main()
