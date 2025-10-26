from solr.setup import core, schema
from solr.usage import document, query

if __name__ == "__main__":
    core.main()
    schema.main()
    document.main()
    query.main()
