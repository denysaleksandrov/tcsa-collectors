import io
import multiprocessing
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process
from queue import Queue
from requests.auth import HTTPBasicAuth

from avro.io import DatumReader, BinaryDecoder
from avro.schema import parse
from confluent_kafka import Consumer
from confluent_kafka.cimpl import KafkaException
from vmware.tcsa.collector_sdk.collectors.stream_collector import StreamCollector
from vmware.tcsa.collector_sdk.models.base import TCOBase
from vmware.tcsa.collector_sdk.models.metric import TCOMetric


class MultiThreadedKafkaCollector(StreamCollector):

    def __init__(self, logger, config) -> None:
        self._config = config
        self.event = multiprocessing.Event()
        self.retries = 0
        super().__init__(logger, config)

    # override only if you want to change the default method execution sequence from collect->transform->publish
    def invoke(self, command: chr):
        self.collect()

    def collect(self):
        workers = []
        num_workers = self._config.get_num_workers
        while True:
            try:
                if self.event.is_set():
                    print("Exiting all child process..")
                    for i in workers:
                        i.terminate()
                    sys.exit(1)
                num_alive = len([w for w in workers if w.is_alive()])
                if num_workers == num_alive:
                    continue
                for _ in range(num_workers - num_alive):
                    p = Process(target=self._consume, daemon=True, args=())
                    p.start()
                    workers.append(p)
                    self._logger.info('Starting worker #%s', p.pid)
            except Exception as e:
                print("Exception in process ", e)

    def _consume(self):
        consumer_config = {}
        num_threads = self._config.get_num_threads
        thread_pool_executor = ThreadPoolExecutor(max_workers=num_threads)
        consumer_config['bootstrap.servers'] = self._config.get_bootstrap_server

        consumer_config['group.id'] = self._config.get_group_id
        consumer_config['auto.offset.reset'] = self._config.get_auto_offset_reset
        consumer_config["error_cb"] = self.error_callback
        topics = self._config.get_topic_name
        self._logger.info(
            '#%s - Starting consumer group=%s, topic=%s', os.getpid(), self._config.get_group_id, topics)
        # consumer = Consumer(consumer_config)
        consumer = Consumer(consumer_config)
        consumer.subscribe([topics])
        msg_queue = Queue(maxsize=num_threads)
        while True:
            self._logger.info('#%s - Waiting for message...', os.getpid())
            try:
                msg = consumer.poll(60)
                if msg is None:
                    continue
                if msg.error():
                    self._logger.info(
                        '#%s - Consumer error: %s', os.getpid(), msg.error()
                    )
                    raise KafkaException(msg.error())
                msg_queue.put(msg)

                self._logger.info("Kafka Message Consumed -- %s ", msg)
                # Use default daemon=False to stop threads gracefully in order to
                # release resources properly.
                thread_pool_executor.submit(self._transform_message, msg_queue, consumer)
            except Exception as e:
                self._logger.error('#%s - Worker terminated.', os.getpid(), e)
                self.retries = self.retries + 1
                if self.retries >= 2 * self._config.get_num_workers:
                    self.event.set()
                try:
                    consumer.close()
                except Exception as ex:
                    self._logger.error("exception while closing consumer", ex)

    def transform(self):
        pass

    def _transform_message(self, msg_queue, consumer) -> TCOBase:
        # apply custom transform on collected object
        self._logger.info("started transform on data")
        msg = msg_queue.get(timeout=60)  # Set timeout to care for POSIX<3.0 and Windows.
        self._logger.info(
            '#%sT%s - Received message: %s', os.getpid(), threading.get_ident(), msg.value())
        output_data = {}

        schema_registry_url = self._config.get_schema_registry_url

        print("Schema Reg URL = ", schema_registry_url)

        avro_schema = self.fetch_schema_from_registry(schema_registry_url, self._config.get_topic_name,
                                                      self._config.get_basic_auth_username, self._config.get_basic_auth_password)
        self._logger.info("avro_schema -- %s ", avro_schema)

        avro_data = msg.value()
        self._logger.info("avro_data -- %s ", avro_data)
        deserialized_data = self.deserialize_avro(avro_data, avro_schema)
        self._logger.info("deserialized_data -- %s ", deserialized_data)

        output_data['instance'] = deserialized_data.get("labels").get("instance")
        output_data['type'] = 'Kafka-Custom-Collector'
        output_data['metricType'] = deserialized_data.get("labels").get("app")
        output_data['timestamp'] = deserialized_data.get("labels").get("timestamp")
        output_data['processedTimestamp'] = deserialized_data.get("labels").get("timestamp")
        properties = {}
        properties['entityName'] = deserialized_data.get("labels").get("name")
        properties["dataSource"] = deserialized_data.get("labels").get("kubernetes_pod_name")
        properties["deviceName"] = deserialized_data.get("labels").get("cnfc_uuid")
        properties["entityType"] = deserialized_data.get("labels").get("nfType")
        properties["deviceType"] = deserialized_data.get("labels").get("kubernetes_namespace")
        properties["ip"] = deserialized_data.get("labels").get("instance")
        output_data['properties'] = properties
        metrics = {'sample': deserialized_data.get("labels").get("value")}
        output_data['metrics'] = metrics
        tags = {'tag1': "Custom Tag", 'deviceName': deserialized_data.get("labels").get("cnfc_uuid")}
        output_data['tags'] = tags
        self._logger.info("transform completed", output_data)
        metric = TCOMetric(output_data.get("instance"), output_data.get("metricType"), output_data.get("timestamp"),
                           output_data.get("processedTimestamp"),
                           output_data.get("type"), output_data.get("metrics"), output_data.get("properties"),
                           output_data.get("tags"))
        self.publish(metric)
        msg_queue.task_done()
        if self.retries > 0:
            self.retries = 0
        consumer.commit(msg)

    def error_callback(self, err):
        print("callback hit!", err)
        raise KafkaException("Error in kafka ")

    def fetch_schema_from_registry(self, schema_registry_url, topic_name, user_name, password):
        import requests
        response = requests.get(f"{schema_registry_url}/subjects/{topic_name}-value/versions/latest",
                                auth=HTTPBasicAuth(user_name, password))
        schema = response.json()["schema"]
        return parse(schema)

    def deserialize_avro(self, avro_data, avro_schema):
        bytes_reader = io.BytesIO(avro_data)
        bytes_reader.seek(5)
        decoder = BinaryDecoder(bytes_reader)
        reader = DatumReader(avro_schema)
        return reader.read(decoder)
