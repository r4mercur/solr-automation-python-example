import json
import logging

import pika
import pysolr

from solr.usage.document import get_solr_client
from solr.util import require_env, setup_logging

logger = logging.getLogger(__name__)

QUEUE_NAME = "solr_import_queue"


def import_message(solr: pysolr.Solr, body: bytes) -> None:
    data = json.loads(body)
    documents = data if isinstance(data, list) else [data]
    solr.add(documents)
    solr.commit()


def create_callback(solr: pysolr.Solr):
    def callback(ch, method, _, body):
        try:
            import_message(solr, body)
            logger.info("Data imported successfully: %s", body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error("Error importing data: %s", e)
            # requeue=False: a broken message would otherwise be redelivered forever
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    return callback


def main() -> None:
    setup_logging()
    solr_url, collection_name, rabbitmq_url = require_env(
        "SOLR_URL", "SOLR_COLLECTION", "RABBITMQ_URL"
    )
    solr = get_solr_client(solr_url, collection_name)

    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=create_callback(solr))

    logger.info("Waiting for messages. To exit press CTRL+C")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
