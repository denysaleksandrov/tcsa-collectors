import json
import multiprocessing
import sys
import time

from vmware.tcsa.collector_sdk.collectors.stream_collector import StreamCollector
from confluent_kafka import Consumer
from concurrent.futures import ThreadPoolExecutor
import pathlib
from vmware.tcsa.collector_sdk.models.base import TCOBase
from vmware.tcsa.collector_sdk.models.metric import TCOMetric
from multiprocessing import Process, Manager
from vmware.tcsa.collector_sdk.models.event import TCOEvent
from queue import Queue
import os
import threading
from confluent_kafka.cimpl import KafkaException, KafkaError
from kafka_custom_ves_collector.ves_utils import convert_to_tco_metrics



class MultiThreadedKafkaCollector(StreamCollector):

    def __init__(self, logger, config) -> None:
        self._config = config
        self.event = multiprocessing.Event()
        self.retries = 0
        current_dir=pathlib.Path(__file__).parent.resolve()
        self._ves_schema=self.read_json_file(os.path.join(current_dir,"CommonEventFormat_30.1.1_ONAP.json"))
        self._ves_metrics_mapper = self.read_json_file(os.path.join(current_dir, "mapper1.json"))
        self._ves_fault_mapper = self.read_json_file(os.path.join(current_dir, "fault_mapper.json"))
        self._pnregistration_mapper = self.read_json_file(os.path.join(current_dir, "pnfRegistrationMapper.json"))
        super().__init__(logger, config)



    def read_json_file(self, filename):
        with open(filename) as json_data:
            data = json.load(json_data)
            return data


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
        pass

    def _transform_message(self, msg_queue, consumer) -> TCOBase:
        # apply custom transform on collected object
        self._logger.info("started transform on data")
        msg = msg_queue.get(timeout=60)  # Set timeout to care for POSIX<3.0 and Windows.
        self._logger.info(
            '#%sT%s - Received message: %s', os.getpid(), threading.get_ident(), msg.value().decode('utf-8'))
        collected_data = json.loads(msg.value().decode('utf-8'))
        output=None
        if collected_data.get('event').get('commonEventHeader').get('domain') == 'measurement':
            tco_metrics = convert_to_tco_metrics(self._ves_metrics_mapper, collected_data, "metrics",self._ves_schema)
            output=TCOMetric.from_dict(tco_metrics)
        if collected_data.get('event').get('commonEventHeader').get('domain') == 'fault':
            tco_event = convert_to_tco_metrics(self._ves_fault_mapper, collected_data, "events",self._ves_schema)
            output=TCOEvent.from_dict(tco_event)
            # output=tco_event
        if collected_data.get('event').get('commonEventHeader').get('domain')=='pnfRegistration':
            tco_event = convert_to_tco_metrics(self._pnregistration_mapper,collected_data, "events",self._ves_schema)
            output = TCOEvent.from_dict(tco_event)
        self.publish(output)
        msg_queue.task_done()
        if self.retries > 0:
            self.retries = 0
        consumer.commit(msg)

    def error_callback(self, err):
        print("callback hit!", err)
        raise KafkaException("Error in kafka ")