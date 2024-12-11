import abc
import six
import json
import urllib3
import datetime

from vmware.tcsa.collector_sdk.collect.http import rest_client
from vmware.tcsa.collector_sdk.collect.http.rest_configuration import RestConfiguration
from vmware.tcsa.collector_sdk.collectors.batch_collector import BatchCollector
from vmware.tcsa.collector_sdk.models.event import TCOEvent

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
                "/events",
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
            event = TCOEvent(Source=collected_data.get("Source"), Name=collected_data.get("Name"),
                            InstanceName=collected_data.get("InstanceName"), State=collected_data.get("State"),
                            Severity=collected_data.get("Severity"),
                            ProcessedTimeStamp=collected_data.get("ProcessedTimeStamp"),
                            Timestamp=collected_data.get("Timestamp"), DisplayName=collected_data.get("DisplayName"),
                            EventDisplayName=collected_data.get("EventDisplayName"),
                            ClassName=collected_data.get("ClassName"),
                            ClassDisplayName=collected_data.get("ClassDisplayName"),
                            InstanceDisplayName=collected_data.get("InstanceDisplayName"),
                            ElementClassName=collected_data.get("ElementClassName"),
                            ElementName=collected_data.get("ElementName"),
                            EventName=collected_data.get("EventName"), EventState=collected_data.get("EventState"),
                            EventText=collected_data.get("EventText"), EventType=collected_data.get("EventType"),
                            Acknowledged=collected_data.get("Acknowledged"), Active=collected_data.get("Active"),
                            Category=collected_data.get("Category"), Certainty=collected_data.get("Certainty"),
                            ClearOnAcknowledge=collected_data.get("ClearOnAcknowledge"),
                            Impact=collected_data.get("Impact"), InMaintenance=collected_data.get("InMaintenance"),
                            IsProblem=collected_data.get("IsProblem"), IsRoot=collected_data.get("IsRoot"),
                            PollingID=collected_data.get("PollingID"), PollingState=collected_data.get("PollingState"),
                            SourceDomainName=collected_data.get("SourceDomainName"),
                            SourceEventType=collected_data.get("SourceEventType"),
                            SourceInfo=collected_data.get("SourceInfo"),
                            SourceSpecific=collected_data.get("SourceSpecific"),
                            TroubleTicketID=collected_data.get("TroubleTicketID"), Owner=collected_data.get("Owner"),
                            ToolInfo=collected_data.get("ToolInfo"), OccurrenceCount=collected_data.get("OccurrenceCount"),
                            FirstNotifiedAt=collected_data.get("FirstNotifiedAt"),
                            LastChangedAt=collected_data.get("LastChangedAt"),
                            LastNotifiedAt=collected_data.get("LastNotifiedAt"),
                            LastClearedAt=collected_data.get("LastClearedAt"),
                            AcknowledgmentTime=collected_data.get("AcknowledgmentTime"), tags=collected_data.get("tags"),
                            properties=collected_data.get("properties"))
            return event
        return None
