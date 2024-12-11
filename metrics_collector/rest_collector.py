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
        self._logger.info("Metrics custom API started collect()")
        configuration = RestConfiguration()
        #configuration.verify_ssl = self._config.get_verify_ssl
        configuration.host = self._config.get_host
        #configuration.username = self._config.get_username
        #configuration.password = self._config.get_password
        self._logger.info(configuration.host)

        try:
            client = rest_client.RestClient(
                configuration=configuration
            )
            res = client.call_api(
                "/metrics",
                "GET",
                _preload_content=False,
                _return_http_data_only=True,
            )

            self._logger.info(f"status: {res.status}")
            if res.status == 200:
                string = res.read().decode("utf-8")
                raw_data = json.loads(string)
                return raw_data

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
            self._logger.info("transform completed", collected_data)
            metric = TCOMetric(
                collected_data.get("instance"),
                collected_data.get("metricType"),
                collected_data.get("timestamp"),
                collected_data.get("processedTimestamp"),
                collected_data.get("type"),
                collected_data.get("metrics"),
                collected_data.get("properties"),
                collected_data.get("tags"),
            )
            return metric
        return None
