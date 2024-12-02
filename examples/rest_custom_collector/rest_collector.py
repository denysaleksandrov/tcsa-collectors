import json
import abc
import six
from vmware.tcsa.collector_sdk.collect.http import rest_client
from vmware.tcsa.collector_sdk.collect.http.rest_configuration import RestConfiguration
from vmware.tcsa.collector_sdk.collectors.batch_collector import BatchCollector
from vmware.tcsa.collector_sdk.models.metric import TCOMetric


class RestCollector(BatchCollector):

    def __init__(self, logger, config: dict) -> None:
        self._config = config
        super().__init__(logger, config)

    def collect(self):
        self._logger.info("started collect()")
        configuration = RestConfiguration()
        configuration.verify_ssl = self._config.get_verify_ssl
        configuration.host = self._config.get_host
        self._logger.info(configuration.host)

        try:
            res = rest_client.RestClient(configuration=configuration).call_api("/httpdemo", 'GET',
                                                                               _preload_content=False,
                                                                               _return_http_data_only=True)

            self._logger.info("status- %s", res.status)
            if res.status == 200:
                string = res.read().decode('utf-8')
                collected_data = json.loads(string)
                self._logger.info(collected_data)
                return collected_data

        except Exception as e:
            self._logger.error("error in processing data %s", e.__cause__)

    def transform(self):
        collected_data = self._collected_data
        if collected_data is not None:
            # apply custom transform on collected object
            self._logger.info("started transform on data %s", collected_data)
            output_data = {}
            output_data['instance'] = collected_data.get("labels").get("instance")
            output_data['metricType'] = collected_data.get("labels").get("app")
            output_data['type'] = 'Rest-Custom-Collector'
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
        return None
