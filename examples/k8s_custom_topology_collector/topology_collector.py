import logging
import logging.config
import os
import shutil
import time
import base64

from vmware.tcsa.collector_sdk.collectors.batch_collector import BatchCollector
from vmware.tcsa.collector_sdk.models.base import TCOBase
from kubernetes import client, config, watch
from vmware.tcsa.collector_sdk.models.topology_models.sam.kubernetes_pod import KubernetesPod
from vmware.tcsa.collector_sdk.models.topology_models.sam.kubernetes_worker import KubernetesWorker


class TopologyCollector(BatchCollector):

    def __init__(self, logger, config: dict) -> None:
        self._config = config
        super().__init__(logger, config)

    def invoke(self, command: chr) -> TCOBase:
        if self.input_file and self.input_file != '':
            self.collect_from_file()
        else:
            self.collect()

    def collect(self):
        self.setK8LogLevel()
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

        api = client.CoreV1Api(client.ApiClient(configuration))

        res = api.list_node()
        for node in res.items:
            field_selector = 'spec.nodeName=' + node.metadata.name
            node = self.createnode(node.metadata.name)
            ret = api.list_pod_for_all_namespaces(watch=False, field_selector=field_selector)
            for pod in ret.items:
                self._collected_data = pod
                res = self.transform_message()
                node.add_Contains(res)
            self.publish(node)
        return self._collected_data

    def transform_message(self):
        self._logger.info("started transform()")
        collected_data = self._collected_data
        pod = TCOBase()
        if collected_data is not None:
            # apply custom transform on collected object
            pod = self.createpod()
            node = self.createnode(collected_data.spec.node_name)
            pod.add_ContainedBy(node)
            self.publish(pod)
        return pod

    def transform(self):
        self._logger.info("started transform()")
        collected_data = self._collected_data
        pod = collected_data = self._collected_data
        discoveryID = "INCHARGE-SA-PRES-vIMS"
        timestamp = round(time.time() * 1000)
        name = collected_data.get('metadata').get('name')
        domain = "INCHARGE-SA-PRES-vIMS"
        source = "primary"
        jobID = str(round(time.time() * 1000))
        groupName = "group"
        action = "r"
        forceRefresh = True
        collectorType = "k8s_custom_topology_collector-rest"
        initialized = True
        ID = round(time.time() * 1000)
        value = 0.0
        metrics = {}
        properties = {}
        relations = []
        pod = KubernetesPod(discoveryID=discoveryID, timestamp=timestamp, name=name, type="KubernetesPod",
                            domain=domain, Source=source, jobID=jobID, groupName=groupName, action=action,
                            forceRefresh=forceRefresh, collectorType=collectorType, initialized=initialized, ID=ID,
                            value=value, metrics=metrics, properties=properties, relations=relations)
        return pod

    def createnode(self, nodename):
        collected_data = self._collected_data
        Source = "primary"
        forceRefresh = True
        collectorType = "k8s_custom_topology_collector-rest"
        discoveryID = "INCHARGE-SA-PRES-vIMS"
        jobID = str(round(time.time() * 1000))
        groupName = "group"
        name = nodename
        action = "r"
        initialized = True
        metrics = {}
        value = 0.0
        domain = "INCHARGE-SA-PRES-vIMS"
        relations = []
        properties = {}
        ID = round(time.time() * 1000)
        timestamp = round(time.time() * 1000)
        node = KubernetesWorker(discoveryID=discoveryID, timestamp=timestamp, name=name,
                                type="KubernetesWorker", domain=domain, Source=Source,
                                jobID=jobID, groupName=groupName, action=action, forceRefresh=forceRefresh,
                                collectorType=collectorType, initialized=initialized, ID=ID,
                                value=value, metrics=metrics, properties=properties, relations=relations)
        return node

    def createpod(self):
        collected_data = self._collected_data
        discoveryID = "INCHARGE-SA-PRES-vIMS"
        timestamp = round(time.time() * 1000)
        name = collected_data.metadata.name
        domain = "INCHARGE-SA-PRES-vIMS"
        source = "primary"
        jobID = str(round(time.time() * 1000))
        groupName = "group"
        action = "r"
        forceRefresh = True
        collectorType = "k8s_custom_topology_collector-rest"
        initialized = True
        ID = round(time.time() * 1000)
        value = 0.0
        metrics = {}
        properties = {}
        relations = []
        pod = KubernetesPod(discoveryID=discoveryID, timestamp=timestamp, name=name, type="KubernetesPod",
                            domain=domain, Source=source, jobID=jobID, groupName=groupName, action=action,
                            forceRefresh=forceRefresh, collectorType=collectorType, initialized=initialized, ID=ID,
                            value=value, metrics=metrics, properties=properties, relations=relations)
        return pod

    def setK8LogLevel(self):
        k8s_log_level = "INFO"
        logging_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'simple': {
                    'format': '%(asctime)s [%(levelname)s] %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S',
                },
            },
            'handlers': {
                'console': {
                    'level': 'DEBUG',
                    'class': 'logging.StreamHandler',
                    'formatter': 'simple',
                },
            },
            'loggers': {
                'kubernetes': {
                    'handlers': ['console'],
                    'level': k8s_log_level,
                    'propagate': False,
                },
            },
        }
        logging.config.dictConfig(logging_config)
