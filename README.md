# Solr Automation Example

This is an example of how to automate Solr using the Solr API. The example is written in Python and uses the requests library to make HTTP requests to the Solr API.

### Setup local solr instance

Use the docker-compose file to setup a local Solr instance.

```bash
docker-compose up -d
```

### Workflow

1. Create the core with the name `core.py` script.
2. Update the schema with the `schema.py` script.
3. Create a document with the `document.py` script.
4. Test the document with the `query.py` script.

