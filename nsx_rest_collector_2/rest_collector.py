import abc
import six
import json
import urllib3
import datetime

from vmware.tcsa.collector_sdk.collect.http import rest_client
from vmware.tcsa.collector_sdk.collect.http.rest_configuration import RestConfiguration
from vmware.tcsa.collector_sdk.collectors.batch_collector import BatchCollector
from vmware.tcsa.collector_sdk.models.metric import TCOMetric

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RestCollector(BatchCollector):

    def __init__(self, logger, config: dict) -> None:
        self._config = config
        super().__init__(logger, config)

    def collect(self):
        self._logger.info("NSX custom API started collect()")
        configuration = RestConfiguration()
        configuration.verify_ssl = self._config.get_verify_ssl
        configuration.host = self._config.get_host
        configuration.username = self._config.get_username
        configuration.password = self._config.get_password
        self._logger.info(configuration.host)

        try:
            client = rest_client.RestClient(
                configuration=configuration,
                header_name="Authorization",
                header_value=configuration.get_basic_auth_token(),
            )
            res = client.call_api(
                "/policy/api/v1/infra/tier-0s/Border-T0/locale-services/default/interfaces/edge01-uplink1/statistics/summary",
                "GET",
                _preload_content=False,
                _return_http_data_only=True,
            )

            self._logger.info(f"status: {res.status}")
            if res.status == 200:
                string = res.read().decode("utf-8")
                raw_data = json.loads(string)
                nsx_ip = configuration.host.lstrip("https://")
                labels = {
                    "instance": nsx_ip + ":Border-T0:edge01-uplink1",
                    "name": "edge01-uplink1",
                    "deviceName": "Border-T0",
                    "timestamp": raw_data.get("last_update_timestamp"),
                    "value": raw_data.get("rx").get("malformed_dropped_packets"),
                    "nsx_instance": nsx_ip,
                    "metric_type": "rx_malformed_dropped_packets",
                }
                collected_data = {"labels": labels}
                # self._logger.info(collected_data)
                return collected_data

        except Exception as e:
            body = json.loads(e.body)
            self._logger.error(
                f"error in processing data, HTTP status code: {e.status}"
            )
            self._logger.error(
                f"error in processing data, reason: {body['error_message']}"
            )

    def transform(self):
        collected_data = self._collected_data
        if collected_data is not None:
            # apply custom transform on collected object
            self._logger.info(f"started transform on data {collected_data}")
            output_data = {}
            output_data["instance"] = collected_data.get("labels").get("instance")
            output_data["metricType"] = collected_data.get("labels").get("metric_type")
            output_data["type"] = "Rest-Custom-Collector"
            output_data["timestamp"] = collected_data.get("labels").get("timestamp")
            output_data["processedTimestamp"] = collected_data.get("labels").get(
                "timestamp"
            )
            properties = {}
            properties["entityName"] = collected_data.get("labels").get("name")
            properties["dataSource"] = collected_data.get("labels").get("nsx_instance")
            properties["deviceName"] = collected_data.get("labels").get("deviceName")
            properties["entityType"] = "Interface"
            properties["deviceType"] = "nsxEdge"
            properties["ip"] = collected_data.get("labels").get("nsx_instance")
            output_data["properties"] = properties
            metrics = {"sample": collected_data.get("labels").get("value")}
            output_data["metrics"] = metrics
            tags = {
                "hostname": collected_data.get("labels").get("deviceName"),
                "deviceName": collected_data.get("labels").get("deviceName"),
            }
            output_data["tags"] = tags
            self._logger.info("transform completed", output_data)
            metric = TCOMetric(
                output_data.get("instance"),
                output_data.get("metricType"),
                output_data.get("timestamp"),
                output_data.get("processedTimestamp"),
                output_data.get("type"),
                output_data.get("metrics"),
                output_data.get("properties"),
                output_data.get("tags"),
            )
            return metric
        return None
