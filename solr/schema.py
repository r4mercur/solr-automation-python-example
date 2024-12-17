import os
import requests
import json

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    solr_url = os.getenv('SOLR_URL')
    collection_name = os.getenv('SOLR_COLLECTION')

    schema_file_path = os.path.join(os.path.dirname(__file__), '../json/fields.json')
    with open(schema_file_path, 'r') as schema_file:
        schema = json.load(schema_file)

    update_solr_schema(solr_url, collection_name, schema)
    reload_solr_collection(solr_url, collection_name)

def update_solr_schema(temp_solr_url: str, temp_collection_name: str, temp_schema: dict) -> None:
    schema_url = f'{temp_solr_url}/{temp_collection_name}/schema'
    response = requests.get(schema_url)

    if response.status_code != 200:
        print(f'Failed to retrieve current schema: {response.text}')
        return

    current_schema = response.json()
    temp_current_schema = current_schema.get('schema', {})

    schema_version = temp_current_schema.get('version')
    existing_fields = {field['name'] for field in temp_current_schema.get('fields', [])}

    new_fields = [field for field in temp_schema.get('add-field', [])
                  if field['name'] not in existing_fields]

    if not new_fields:
        print(f'No new fields to add, to schema with version: {schema_version}')
        return

    update_payload = {'add-field': new_fields}
    response = requests.post(schema_url, json=update_payload)
    if response.status_code == 200:
        print('Schema updated successfully.')
    else:
        print(f'Failed to update schema: {response.text}')


def reload_solr_collection(temp_solr_url: str, temp_collection_name: str) -> None:
    reload_url = f'{temp_solr_url}/admin/collections?action=RELOAD&name={temp_collection_name}'
    response = requests.get(reload_url)
    if response.status_code == 200:
        print(f'Collection {temp_collection_name} reloaded successfully.')
    else:
        print(f'Failed to reload collection {temp_collection_name}: {response.text}')


if __name__ == '__main__':
    main()