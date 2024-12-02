import json
import abc
import six
import time
from vmware.tcsa.collector_sdk.collect.http import rest_client
from vmware.tcsa.collector_sdk.collect.http.rest_configuration import RestConfiguration
from vmware.tcsa.collector_sdk.collectors.batch_collector import BatchCollector
from vmware.tcsa.collector_sdk.models.topology import TCOTopology
from vmware.tcsa.collector_sdk.models.base import TCOBase
from nfvsol_collector.extract_utils import extract_vnfs, extract_cell_site_details, extract_sol_services_or_parents


class NFVSolCollector(BatchCollector):

    def __init__(self, logger, config: dict) -> None:
        self._config = config
        super().__init__(logger, config)

    def invoke(self, command: chr) -> TCOBase:
        self.collect()

    def collect(self):
        publish_data = []
        self._logger.info("This Collector collects data from VNF instances")
        start_message = self.create_start_message()
        self.collect_and_transform_vnfc_data(publish_data, start_message)
        self.collect_and_transform_cell_site_data(publish_data, start_message)
        end_message = self.create_end_message(start_message, publish_data)
        publish_data.append(start_message)
        publish_data.append(end_message)

        for data in publish_data:
            self.publish(data)

    def transform(self) -> TCOBase:
        pass

    def collect_and_transform_vnfc_data(self, publish_data, start_message):

        self._logger.info("starting to collect VNF instances data")
        vnfc_data = None
        cnf_data = {}
        configuration = RestConfiguration()
        configuration.verify_ssl = self._config.get_verify_ssl
        configuration.host = self._config.get_host
        configuration.username = self._config.get_username
        configuration.password = self._config.get_password
        self._logger.info(configuration.host)
        try:
            res = rest_client.RestClient(configuration=configuration).call_api(
                "/telco/api/vnflcm/v2/extension/vnf_instances", 'GET',
                _preload_content=False,
                _return_http_data_only=True)
            self._logger.info("status- %s", res.status)
            if res.status == 200:
                string = res.data.decode('utf-8')
                vnfc_data = json.loads(string)
                self._logger.info(vnfc_data)
        except Exception as e:
            self._logger.error("error in processing data %s", e.__cause__)

        if vnfc_data:
            for vnf in vnfc_data:
                # RETRIEVE CNF INSTANCES
                parent_toplogy = extract_vnfs(vnf, self._config.get_host, publish_data, start_message)
                id = vnf.get("id")
                try:
                    cnf_url = "/hybridity/api/vnflcm/v1/cnf_instances/{id}/inventory".format(id=id)
                    res = rest_client.RestClient(configuration=configuration).call_api(cnf_url, 'GET',
                                                                                       _preload_content=False,
                                                                                       _return_http_data_only=True)

                    self._logger.info("status- %s", res.status)
                    if res.status == 200:
                        string = res.data.decode('utf-8')
                        cnf_data = json.loads(string)
                except Exception as e:
                    self._logger.error("error in processing data %s", e.__cause__)
                for cnf in cnf_data.get("items", []):
                    extract_sol_services_or_parents(cnf, start_message, publish_data, parent_toplogy)

    def collect_and_transform_cell_site_data(self, publish_data, start_message):

        self._logger.info("starting to collect VNF instances data")
        cell_site_data = {}
        configuration = RestConfiguration()
        configuration.verify_ssl = self._config.get_verify_ssl
        configuration.host = self._config.get_host
        configuration.username = self._config.get_username
        configuration.password = self._config.get_password
        self._logger.info(configuration.host)
        try:
            res = rest_client.RestClient(configuration=configuration).call_api("/hybridity/api/ztp/status", 'GET',
                                                                               _preload_content=False,
                                                                               _return_http_data_only=True)
            self._logger.info("status- %s", res.status)
            if res.status == 200:
                string = res.data.decode('utf-8')
                cell_site_data = json.loads(string)
                self._logger.info(cell_site_data)

        except Exception as e:
            self._logger.error("error in processing data %s", e.__cause__)
        for cell_site in cell_site_data.get("domains", []):
            extract_cell_site_details(cell_site, publish_data, start_message)

    def create_start_message(self):
        timestamp = round(time.time() * 1000)
        start_message = TCOTopology()
        start_message.type = "START"
        start_message.Source = "primary"
        start_message.forceRefresh = True
        start_message.collectorType = "custom-topology-collector-rest"
        start_message.discoveryID = "INCHARGE-SA-PRES-vIMS"
        start_message.jobID = str(timestamp)
        start_message.groupName = "group"
        start_message.name = "custom-topology-collector"
        start_message.action = "r"
        start_message.initialized = True
        start_message.msgCount = 0
        start_message.metrics = {}
        start_message.relations = []
        start_message.properties = {
            "observer": "TRUE",
            "OpenedAt": timestamp,
            "context-name": "INCHARGE-SA-PRES-vIMS",
            "source": "INCHARGE-SA-PRES-vIMS",
            "type": "START",
            "Source": "primary",
            "collector-name": "custom-topology-collector"
        }
        start_message.timestamp = timestamp

        return start_message

    def create_end_message(self, start_message, publish_data):
        end_message = TCOTopology()
        end_message.type = "END"
        end_message.Source = start_message.Source
        end_message.forceRefresh = start_message.forceRefresh
        end_message.collectorType = start_message.collectorType
        end_message.discoveryID = start_message.discoveryID
        end_message.jobID = start_message.jobID
        end_message.groupName = start_message.groupName
        end_message.name = start_message.name
        end_message.action = start_message.action
        end_message.initialized = start_message.initialized
        end_message.msgCount = len(publish_data)
        end_message.metrics = {}
        end_message.relations = []
        end_message.properties = {
            "observer": "TRUE",
            "OpenedAt": start_message.timestamp,
            "context-name": "INCHARGE-SA-PRES-vIMS",
            "type": "END",
            "Source": "primary",
            "collector-name": "custom-topology-collector"
        }
        end_message.timestamp: start_message.timestamp
        return end_message
