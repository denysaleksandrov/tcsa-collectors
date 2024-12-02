
import json
import abc
import six
from vmware.tcsa.collector_sdk.collect.http import rest_client
from vmware.tcsa.collector_sdk.collect.http.rest_configuration import RestConfiguration
from vmware.tcsa.collector_sdk.collectors.batch_collector import BatchCollector
from vmware.tcsa.collector_sdk.models.base import TCOBase
from vmware.tcsa.collector_sdk.models.metric import TCOMetric


class RestCollector(BatchCollector):

    def __init__(self, logger, config: dict) -> None:
        self._config = config
        super().__init__(logger, config)

    def invoke(self, command: chr) -> TCOBase:
        self._collected_data = self.collect()
        self._transformed_data = self.transform()

    def collect(self):
        self._logger.info("started collect()")
        configuration = RestConfiguration()
        configuration.verify_ssl = self._config.get_verify_ssl
        configuration.host = self._config.get_host
        self._logger.info(configuration.host)

        try:
            aci_token_res_data = rest_client.RestClient(configuration=configuration) \
                .call_api("/api/aaaLogin.json",
                          'POST',
                          body={
                              "aaaUser": {
                                  "attributes": {
                                      "name": "admin",
                                      "pwd": "!v3G@!4@Y"}}},
                          _preload_content=False,
                          _return_http_data_only=True)

            self._logger.info("headers [{data}] ".format(data=aci_token_res_data.getheaders()))

            configuration.cookie = aci_token_res_data.getheader(name="Set-Cookie")

            aci_res_node_data = rest_client.RestClient(configuration=configuration).call_api(
                "/api/class/fabricNode.json", 'GET',
                _preload_content=False,
                _return_http_data_only=True)

            self._logger.info("Collected Data [{data}] ".format(data=aci_token_res_data.data))
            self._logger.info("status- %s", aci_res_node_data.status)
            if aci_res_node_data.status == 200:
                string = aci_res_node_data.read().decode('utf-8')
                collected_data = json.loads(string)
                self._logger.info(collected_data)
                return collected_data

        except Exception as e:
            self._logger.error("error in processing data %s", e.__cause__)

    def transform(self):
        collected_data = self._collected_data
        if collected_data is not None:
            # apply custom transform on collected object
            for record in collected_data.get("imdata",[]):
                attributes = record.get("fabricNode",{}).get("attributes",{})
                self._logger.info("started transform on data %s", collected_data)
                output_data = {}
                output_data['instance'] = attributes.get("name")
                output_data['type'] = 'Rest-Custom-Collector'
                output_data['metricType'] = attributes.get("vendor")
                output_data['timestamp'] = attributes.get("modTs")
                output_data['processedTimestamp'] = attributes.get("lastStateModTs")
                properties = {}
                properties['entityName'] = attributes.get("name")
                properties["dataSource"] = attributes.get("monPolDn")
                properties["deviceName"] = attributes.get("dn")
                properties["entityType"] = attributes.get("apicType")
                properties["deviceType"] = attributes.get("nodeType")
                output_data['properties'] = properties
                metrics = {'sample': 0}
                output_data['metrics'] = metrics
                tags = {'tag1': "Custom Tag", 'deviceName': attributes.get("dn")}
                output_data['tags'] = tags
                self._logger.info("transform completed", output_data)
                metric = TCOMetric(output_data.get("instance"), output_data.get("metricType"), output_data.get("timestamp"),
                                   output_data.get("processedTimestamp"),
                                   output_data.get("type"), output_data.get("metrics"), output_data.get("properties"),
                                   output_data.get("tags"))
                self.publish(metric)
            return metric