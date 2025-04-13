import json

import pika

from solr.util import get_solr_client

solr = get_solr_client()
rabbit_url = "amqp://guest:guest@localhost:5672/"
connection = pika.BlockingConnection(pika.ConnectionParameters(rabbit_url))
channel = connection.channel()

queue_name = "solr_import_queue"
channel.queue_declare(queue=queue_name, durable=True)


def callback(ch, method, _, body):
    try:
        data = json.loads(body)
        solr.add(data)
        solr.commit()
        print("Data imported successfully:", data)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print("Error importing data:", e)
        ch.basic_nack(delivery_tag=method.delivery_tag)


channel.basic_consume(queue=queue_name, on_message_callback=callback)

print("Waiting for messages. To exit press CTRL+C")
channel.start_consuming()
