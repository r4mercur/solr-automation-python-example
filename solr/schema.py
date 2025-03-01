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

    current_version = temp_current_schema.get('version', 1.0)
    existing_fields = {field['name'] for field in temp_current_schema.get('fields', [])}
    existing_field_types = {field['name'] for field in temp_current_schema.get('fieldTypes', [])}

    json_fields = {field['name'] for field in temp_schema.get('add-field', [])}
    json_delete_fields = {field['name'] for field in temp_schema.get('delete-field', [])}


    new_field_types = [ft for ft in temp_schema.get('add-field-type', [])
                      if ft['name'] not in existing_field_types]

    new_fields = [field for field in temp_schema.get('add-field', [])
                  if field['name'] not in existing_fields]

    necessary_fields = {'id', '_text_', '_nest_path_', '_root_', '_version_'}
    fields_to_remove = [field for field in existing_fields
                        if field not in json_fields and field not in necessary_fields]
    # Include fields explicitly marked for deletion
    fields_to_remove.extend([field for field in json_delete_fields
                             if field in existing_fields and field not in necessary_fields])

    update_payload = {}

    if new_field_types:
        update_payload['add-field-type'] = new_field_types

    if new_fields:
        update_payload['add-field'] = new_fields

    if fields_to_remove:
        update_payload['delete-field'] = [{'name': field} for field in fields_to_remove]

    if new_field_types:
        print(f'Adding new field types: {new_field_types}')

    if not new_fields and not fields_to_remove:
        print(f'No changes to the schema with version: {current_version}')
        return

    response = requests.post(schema_url, json=update_payload)
    if response.status_code == 200:
        print('Schema updated successfully.')
        commit_url = f'{temp_solr_url}/{temp_collection_name}/update?commit=true'
        commit_response = requests.get(commit_url)
        if commit_response.status_code == 200:
            print('Changes committed successfully.')
        else:
            print(f'Failed to commit changes: {commit_response.text}')
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