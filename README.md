# Solr Automation Example

This is an example of how to automate Solr using the Solr API. 
The example is written in Python and uses the requests library to make HTTP requests to the Solr API.

### Setup local solr instance

Use the docker-compose file to set up a local Solr instance.

```bash
docker-compose up -d
```

### Workflow

1. Create the core with the name `core.py` script.
2. Update the schema with the `schema.py` script.
3. Create a document with the `document.py` script.
4. Test the document with the `query.py` script.
5. (Optional) Enable security with the `security.py` script.

## Schema

The schema is defined in the `schema.py` script. 
The schema defines the fields that are available in the Solr core.
You can adjust the schema to your needs. 

What you would do is add or remove fields from the schema. 
This is done via the json file `fields.json` and at wards executed by the `schema.py` script again.