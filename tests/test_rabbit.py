import json
import os
import threading
import time
import unittest
import uuid

import pika
import pysolr
from dotenv import load_dotenv
from testcontainers.compose import DockerCompose

from solr import create_solr_collection, update_solr_schema


class TestSolrRabbitIntegration(unittest.TestCase):
    def setUp(self):
        self.compose = DockerCompose(
            os.path.dirname(__file__), compose_file_name="docker-compose.test.yml"
        )
        self.compose.start()

        load_dotenv()
        self.solr_url = os.getenv("SOLR_URL")
        self.solr_collection = os.getenv("SOLR_COLLECTION")
        time.sleep(15)

        # create solr collection & update schema
        create_solr_collection(self.solr_url, self.solr_collection)
        schema_file_path = os.path.join(
            os.path.dirname(__file__), "../json/fields.json"
        )
        with open(schema_file_path, "r") as schema_file:
            schema = json.load(schema_file)
            update_solr_schema(self.solr_url, self.solr_collection, schema)

        self.solr = pysolr.Solr(
            f"{self.solr_url}/{self.solr_collection}", always_commit=True
        )

        self.stop_consumer = False
        self.rabbit_url = os.getenv("RABBITMQ_URL")
        self.rabbit_host = "rabbitmq"
        self.connection = None
        self.channel = None
        self._connect_to_rabbit()

        # consumer-thread starting
        self.consumer_thread = threading.Thread(target=self._run_consumer)
        self.consumer_thread.daemon = True
        self.consumer_thread.start()

        print("Consumer-Thread started")

    def tearDown(self):
        self.stop_consumer = True
        if self.connection:
            self.connection.close()

        self.compose.stop()

    def _connect_to_rabbit(self):
        retry = 0
        max_retry = 10

        self.rabbit_host = "localhost"

        while retry < max_retry:
            try:
                print(f"Connection attempt to RabbitMQ: {self.rabbit_host}:5672")
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host=self.rabbit_host, port=5672)
                )
                self.channel = self.connection.channel()
                self.queue_name = "solr_import_queue"
                self.channel.queue_declare(queue=self.queue_name, durable=True)
                print("Connection to RabbitMQ established")
                return
            except Exception as e:
                retry += 1
                print(f"Connection attempt {retry}/{max_retry} to RabbitMQ: {e}")
                time.sleep(2)

        # set none if connection fails
        self.connection = None
        self.channel = None
        raise ConnectionError(
            "Error when trying to connect to RabbitMQ. Check if RabbitMQ is running."
        )

    def _run_consumer(self):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host="localhost")
            )
            channel = connection.channel()
            channel.queue_declare(queue=self.queue_name, durable=True)

            def callback(ch, method, _, body):
                try:
                    print(f"Message received: {body}")
                    data = json.loads(body)

                    if isinstance(data, list):
                        print(f"List with {len(data)} documents received")
                        self.solr.add(data)
                    else:
                        print(f"Single Document: {data['id']}")
                        self.solr.add([data])

                    self.solr.commit()
                    print(f"Document successfully imported: {data}")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as err:
                    print(f"Error when importing: {err}")
                    ch.basic_nack(delivery_tag=method.delivery_tag)

            print("Start consumer with basic_get...")
            while not self.stop_consumer:
                method, properties, body = channel.basic_get(
                    queue=self.queue_name, auto_ack=False
                )
                if method:
                    print("Found message in queue!")
                    callback(channel, method, properties, body)
                time.sleep(0.5)

            connection.close()
        except Exception as e:
            print(f"Error in consumer thread: {str(e)}")

    def test_solr_rabbit_integration(self):
        if self.channel is None:
            self.fail("No connection to RabbitMQ - Test cannot be performed")

        doc_id = str(uuid.uuid4())
        test_doc = {
            "id": doc_id,
            "gender": "Male",
            "age": 30,
            "name": "Integration Test",
            "email": "test@example.com",
            "address": "123 Test St",
            "city": "Berlin",
            "state": "BE",
            "search_for": "Female",
        }

        self.channel.basic_publish(
            exchange="",
            routing_key=self.queue_name,
            body=json.dumps(test_doc),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        print(f"Document published to RabbitMQ: {test_doc}")

        max_retries = 15
        for index in range(max_retries):
            time.sleep(2)
            results = self.solr.search(f"id:{test_doc['id']}")
            if len(results) > 0:
                break

        results = self.solr.search(f"id:{test_doc['id']}")
        self.assertEqual(len(results), 1, "Document not found in Solr")
        self.assertEqual(results.docs[0]["name"], "Integration Test")
        self.assertEqual(results.docs[0]["gender"], "Male")
        self.assertEqual(results.docs[0]["search_for"], "Female")
