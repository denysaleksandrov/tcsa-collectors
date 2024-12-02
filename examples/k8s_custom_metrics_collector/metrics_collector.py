import json
import abc
import os
import shutil

import six
import base64
from vmware.tcsa.collector_sdk.collectors.batch_collector import BatchCollector
from vmware.tcsa.collector_sdk.models.base import TCOBase
from vmware.tcsa.collector_sdk.models.metric import TCOMetric
from kubernetes import client, config


class MetricsCollector(BatchCollector):

    def __init__(self, logger, config: dict) -> None:
        self.collected_data = None
        self._config = config
        super().__init__(logger, config)

    def invoke(self, command: chr) -> TCOBase:
        if self.input_file and self.input_file != '':
            self.collect_from_file()
        else:
            self.collect()

    def collect(self):
        self._logger.info("started collect()")
        configuration = client.Configuration()
        configuration.host = self._config.get_host
        configuration.verify_ssl = self._config.get_verify_ssl
        shutil.rmtree('tmp', ignore_errors=True)
        os.mkdir(os.path.join('', 'tmp'), 0o777)
        text_file = open("tmp/client.crt", "w")
        text_file.write(base64.b64decode(self._config.get_cert_file).decode("utf-8"))
        text_file = open("tmp/ssl.crt", "w")
        text_file.write(base64.b64decode(self._config.get_ssl_ca_cert).decode("utf-8"))
        text_file = open("tmp/client.key", "w")
        text_file.write(base64.b64decode(self._config.get_key_file).decode("utf-8"))

        configuration.cert_file = "tmp/client.crt"
        configuration.ssl_ca_cert = 'tmp/ssl.crt'
        configuration.key_file = 'tmp/client.key'

        text_file.close()

        api = client.CustomObjectsApi(client.ApiClient(configuration))
        k8s_nodes = api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")
        for stats in k8s_nodes['items']:
            self._collected_data = stats
            self._transformed_data = self.transform()
            self.publish(self._transformed_data)
        return None

    def transform(self) -> TCOBase:
        self._logger.info("started transform()")
        collected_data = self._collected_data
        if self._collected_data is not None:
            print("self._collected_data not none: ")
            # apply custom transform on collected object
            output_data = {}
            output_data['instance'] = collected_data.get("metadata").get("labels").get(
                "node.kubernetes.io/instance-type")
            output_data['metricType'] = collected_data.get("metadata").get("labels").get("beta.kubernetes.io/arch")
            output_data['type'] = 'K8S-Custom-Collector'
            output_data['timestamp'] = collected_data.get("metadata").get("creationTimestamp")
            output_data['processedTimestamp'] = collected_data.get("timestamp")
            properties = {}
            properties['entityName'] = collected_data.get("metadata").get("name")
            properties["dataSource"] = collected_data.get("metadata").get("labels").get(
                "node.cluster.x-k8s.io/esxi-host")
            properties["deviceName"] = collected_data.get("metadata").get("name")
            properties["entityType"] = collected_data.get("metadata").get("labels").get(
                "node-role.kubernetes.io/control-plane")
            properties["deviceType"] = collected_data.get("metadata").get("labels").get(
                "node-role.kubernetes.io/control-plane")
            properties["ip"] = collected_data.get("metadata").get("labels").get("node.cluster.x-k8s.io/esxi-host")
            output_data['properties'] = properties
            metrics = {'sample': collected_data.get("usage").get("cpu")}
            output_data['metrics'] = metrics
            tags = {'tag1': "Custom Tag", 'deviceName': collected_data.get("metadata").get("name")}
            output_data['tags'] = tags
            metric = TCOMetric(output_data.get("instance"), output_data.get("metricType"), output_data.get("timestamp"),
                               output_data.get("processedTimestamp"),
                               output_data.get("type"), output_data.get("metrics"), output_data.get("properties"),
                               output_data.get("tags"))
            return metric
        return None
