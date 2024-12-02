import json
import multiprocessing
import sys
import time

from vmware.tcsa.collector_sdk.collectors.stream_collector import StreamCollector
from confluent_kafka import Consumer
from concurrent.futures import ThreadPoolExecutor
from vmware.tcsa.collector_sdk.models.base import TCOBase
from vmware.tcsa.collector_sdk.models.metric import TCOMetric
from multiprocessing import Process, Manager
from queue import Queue
import os
import threading
from confluent_kafka.cimpl import KafkaException, KafkaError


class MultiThreadedKafkaCollector(StreamCollector):

    def __init__(self, logger, config) -> None:
        self._config = config
        self.event = multiprocessing.Event()
        self.retries = 0
        super().__init__(logger, config)

    # override only if you want to change the default method execution sequence from collect->transform->publish
    #def invoke(self, command: chr):
    # self.collect()

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
        # apply custom transform on collected object
        self._logger.info("started transform on data")
        output_data = {}
        collected_data = self._collected_data
        output_data['instance'] = collected_data.get("labels").get("instance")
        output_data['type'] = 'Kafka-Custom-Collector'
        output_data['metricType'] = collected_data.get("labels").get("app")
        output_data['timestamp'] = collected_data.get("labels").get("timestamp")
        output_data['processedTimestamp'] = collected_data.get("labels").get("timestamp")
        properties = {}
        properties['entityName'] = collected_data.get("labels").get("name")
        properties["dataSource"] = collected_data.get("labels").get("kubernetes_pod_name")
        properties["deviceName"] = collected_data.get("labels").get("cnfc_uuid")
        properties["entityType"] = collected_data.get("labels").get("nfType")
        properties["deviceType"] = collected_data.get("labels").get("kubernetes_namespace")
        properties["ip"] = collected_data.get("labels").get("instance")
        output_data['properties'] = properties
        metrics = {'sample': collected_data.get("labels").get("value")}
        output_data['metrics'] = metrics
        tags = {'tag1': "Custom Tag", 'deviceName': collected_data.get("labels").get("cnfc_uuid")}
        output_data['tags'] = tags
        self._logger.info("transform completed", output_data)
        metric = TCOMetric(output_data.get("instance"), output_data.get("metricType"), output_data.get("timestamp"),
                           output_data.get("processedTimestamp"),
                           output_data.get("type"), output_data.get("metrics"), output_data.get("properties"),
                           output_data.get("tags"))
        return metric

    def _transform_message(self, msg_queue, consumer) -> TCOBase:
        # apply custom transform on collected object
        self._logger.info("started transform on data")
        msg = msg_queue.get(timeout=60)  # Set timeout to care for POSIX<3.0 and Windows.
        self._logger.info(
            '#%sT%s - Received message: %s', os.getpid(), threading.get_ident(), msg.value().decode('utf-8'))
        output_data = {}
        collected_data = json.loads(msg.value().decode('utf-8'))
        output_data['instance'] = collected_data.get("labels").get("instance")
        output_data['type'] = 'Kafka-Custom-Collector'
        output_data['metricType'] = collected_data.get("labels").get("app")
        output_data['timestamp'] = collected_data.get("labels").get("timestamp")
        output_data['processedTimestamp'] = collected_data.get("labels").get("timestamp")
        properties = {}
        properties['entityName'] = collected_data.get("labels").get("name")
        properties["dataSource"] = collected_data.get("labels").get("kubernetes_pod_name")
        properties["deviceName"] = collected_data.get("labels").get("cnfc_uuid")
        properties["entityType"] = collected_data.get("labels").get("nfType")
        properties["deviceType"] = collected_data.get("labels").get("kubernetes_namespace")
        properties["ip"] = collected_data.get("labels").get("instance")
        output_data['properties'] = properties
        metrics = {'sample': collected_data.get("labels").get("value")}
        output_data['metrics'] = metrics
        tags = {'tag1': "Custom Tag", 'deviceName': collected_data.get("labels").get("cnfc_uuid")}
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