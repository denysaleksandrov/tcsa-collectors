import os
import shutil
import time

import base64
from vmware.tcsa.collector_sdk.collectors.stream_collector import StreamCollector
from vmware.tcsa.collector_sdk.models.base import TCOBase
from vmware.tcsa.collector_sdk.models.event import TCOEvent
from kubernetes import client, config, watch


class EventsCollector(StreamCollector):

    def __init__(self, logger, config: dict) -> None:
        self.collected_data = None
        self._config = config
        super().__init__(logger, config)

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

        api = client.CoreV1Api(client.ApiClient(configuration))

        w = watch.Watch()
        res = w.stream(api.list_namespace)
        for event in res:
            self._collected_data = event
            self._transformed_data = self.transform_message()
            self.publish(self._transformed_data)
        return None

    def transform(self):
        self._logger.info("started transform()")
        collected_data = self._collected_data
        print("collected_data -", collected_data)
        if self._collected_data is not None:
            # apply custom transform on collected object
            output_data = {}
            output_data['InstanceName'] = collected_data.get('object').get('kind')
            output_data['Source'] = collected_data.get('object').get('metadata').get('labels').get(
                'kubernetes.io/metadata.name')
            output_data['Timestamp'] = round(time.time() * 1000)
            output_data['ProcessedTimeStamp'] = round(time.time() * 1000)
            output_data['Name'] = collected_data.get('object').get('metadata').get('name')
            output_data['State'] = collected_data.get('object').get('status').get('phase')
            output_data["Severity"] = collected_data.get("type")
            output_data["Category"] = collected_data.get("type")
            output_data["EventState"] = collected_data.get('object').get('status').get('phase')
            output_data["ElementName"] = collected_data.get('object').get('metadata').get('name')
            output_data["Owner"] = collected_data.get('object').get('metadata').get('name')
            output_data["EventText"] = collected_data.get("type")
            output_data["EventName"] = collected_data.get("type")
            output_data["DisplayName"] = collected_data.get('object').get('kind')
            output_data["EventDisplayName"] = collected_data.get('object').get('kind')
            output_data["ClassDisplayName"] = collected_data.get('object').get('kind')
            output_data["InstanceDisplayName"] = collected_data.get('object').get('kind')
            output_data["SourceEventType"] = "EVENTS"
            output_data["ClassName"] = collected_data.get('object').get('kind')
            output_data["ElementClassName"] = collected_data.get("type")
            output_data["EventType"] = collected_data.get("type")
            output_data["Acknowledged"] = False
            output_data["Active"] = collected_data.get('object').get('status').get('phase')
            output_data["Certainty"] = collected_data.get('object').get('status').get('phase')
            output_data["ClearOnAcknowledge"] = True
            output_data["Impact"] = collected_data.get('object').get('metadata').get('name')
            output_data["IsProblem"] = True
            output_data["IsRoot"] = True
            output_data["PollingID"] = collected_data.get('object').get('metadata').get('resource_version')
            output_data["PollingState"] = collected_data.get('object').get('status').get('phase')
            output_data["SourceDomainName"] = collected_data.get('object').get('metadata').get('name')
            output_data["SourceInfo"] = collected_data.get('object').get('api_version')
            output_data["SourceSpecific"] = collected_data.get('object').get('api_version')
            output_data["TroubleTicketID"] = collected_data.get('object').get('metadata').get('uid')
            output_data["ToolInfo"] = collected_data.get('object').get('api_version')
            output_data["OccurrenceCount"] = 2
            output_data["FirstNotifiedAt"] = round(time.time() * 1000)
            output_data["LastChangedAt"] = round(time.time() * 1000)
            output_data["LastNotifiedAt"] = round(time.time() * 1000)
            output_data["LastClearedAt"] = round(time.time() * 1000)
            output_data["AcknowledgmentTime"] = 30
            output_data["tags"] = {}
            output_data["properties"] = {}
            output_data["InMaintenance"] = True

            event = TCOEvent(Source=output_data.get("Source"), Name=output_data.get("Name"),
                             InstanceName=output_data.get("InstanceName"), State=output_data.get("State"),
                             Severity=output_data.get("Severity"),
                             ProcessedTimeStamp=output_data.get("ProcessedTimeStamp"),
                             Timestamp=output_data.get("Timestamp"), DisplayName=output_data.get("DisplayName"),
                             EventDisplayName=output_data.get("EventDisplayName"),
                             ClassName=output_data.get("ClassName"),
                             ClassDisplayName=output_data.get("ClassDisplayName"),
                             InstanceDisplayName=output_data.get("InstanceDisplayName"),
                             ElementClassName=output_data.get("ElementClassName"),
                             ElementName=output_data.get("ElementName"),
                             EventName=output_data.get("EventName"), EventState=output_data.get("EventState"),
                             EventText=output_data.get("EventText"), EventType=output_data.get("EventType"),
                             Acknowledged=output_data.get("Acknowledged"), Active=output_data.get("Active"),
                             Category=output_data.get("Category"), Certainty=output_data.get("Certainty"),
                             ClearOnAcknowledge=output_data.get("ClearOnAcknowledge"),
                             Impact=output_data.get("Impact"), InMaintenance=output_data.get("InMaintenance"),
                             IsProblem=output_data.get("IsProblem"), IsRoot=output_data.get("IsRoot"),
                             PollingID=output_data.get("PollingID"), PollingState=output_data.get("PollingState"),
                             SourceDomainName=output_data.get("SourceDomainName"),
                             SourceEventType=output_data.get("SourceEventType"),
                             SourceInfo=output_data.get("SourceInfo"),
                             SourceSpecific=output_data.get("SourceSpecific"),
                             TroubleTicketID=output_data.get("TroubleTicketID"), Owner=output_data.get("Owner"),
                             ToolInfo=output_data.get("ToolInfo"), OccurrenceCount=output_data.get("OccurrenceCount"),
                             FirstNotifiedAt=output_data.get("FirstNotifiedAt"),
                             LastChangedAt=output_data.get("LastChangedAt"),
                             LastNotifiedAt=output_data.get("LastNotifiedAt"),
                             LastClearedAt=output_data.get("LastClearedAt"),
                             AcknowledgmentTime=output_data.get("AcknowledgmentTime"), tags=output_data.get("tags"),
                             properties=output_data.get("properties"))
            return event
        return None


    def transform_message(self):
        self._logger.info("started transform()")
        collected_data = self._collected_data
        if self._collected_data is not None:
            # apply custom transform on collected object
            output_data = {}
            output_data['InstanceName'] = collected_data['object'].kind
            output_data['Source'] = collected_data['object'].metadata.labels.get('kubernetes.io/metadata.name')
            output_data['Timestamp'] = round(time.time() * 1000)
            output_data['ProcessedTimeStamp'] = round(time.time() * 1000)
            output_data['Name'] = collected_data['object'].metadata.name
            output_data['State'] = collected_data['object'].status.phase
            output_data["Severity"] = collected_data.get("type")
            output_data["Category"] = collected_data.get("type")
            output_data["EventState"] = collected_data['object'].status.phase
            output_data["ElementName"] = collected_data['object'].metadata.name
            output_data["Owner"] = collected_data['object'].metadata.name
            output_data["EventText"] = collected_data.get("type")
            output_data["EventName"] = collected_data.get("type")
            output_data["DisplayName"] = collected_data['object'].kind
            output_data["EventDisplayName"] = collected_data['object'].kind
            output_data["ClassDisplayName"] = collected_data['object'].kind
            output_data["InstanceDisplayName"] = collected_data['object'].kind
            output_data["SourceEventType"] = "EVENTS"
            output_data["ClassName"] = collected_data['object'].kind
            output_data["ElementClassName"] = collected_data.get("type")
            output_data["EventType"] = collected_data.get("type")
            output_data["Acknowledged"] = False
            output_data["Active"] = collected_data['object'].status.phase
            output_data["Certainty"] = collected_data['object'].status.phase
            output_data["ClearOnAcknowledge"] = True
            output_data["Impact"] = collected_data['object'].metadata.name
            output_data["IsProblem"] = True
            output_data["IsRoot"] = True
            output_data["PollingID"] = collected_data['object'].metadata.resource_version
            output_data["PollingState"] = collected_data['object'].status.phase
            output_data["SourceDomainName"] = collected_data['object'].metadata.name
            output_data["SourceInfo"] = collected_data['object'].api_version
            output_data["SourceSpecific"] = collected_data['object'].api_version
            output_data["TroubleTicketID"] = collected_data['object'].metadata.uid
            output_data["ToolInfo"] = collected_data['object'].api_version
            output_data["OccurrenceCount"] = 2
            output_data["FirstNotifiedAt"] = round(time.time() * 1000)
            output_data["LastChangedAt"] = round(time.time() * 1000)
            output_data["LastNotifiedAt"] = round(time.time() * 1000)
            output_data["LastClearedAt"] = round(time.time() * 1000)
            output_data["AcknowledgmentTime"] = 30
            output_data["tags"] = {}
            output_data["properties"] = {}
            output_data["InMaintenance"] = True

            event = TCOEvent(Source=output_data.get("Source"), Name=output_data.get("Name"),
                             InstanceName=output_data.get("InstanceName"), State=output_data.get("State"),
                             Severity=output_data.get("Severity"),
                             ProcessedTimeStamp=output_data.get("ProcessedTimeStamp"),
                             Timestamp=output_data.get("Timestamp"), DisplayName=output_data.get("DisplayName"),
                             EventDisplayName=output_data.get("EventDisplayName"),
                             ClassName=output_data.get("ClassName"),
                             ClassDisplayName=output_data.get("ClassDisplayName"),
                             InstanceDisplayName=output_data.get("InstanceDisplayName"),
                             ElementClassName=output_data.get("ElementClassName"),
                             ElementName=output_data.get("ElementName"),
                             EventName=output_data.get("EventName"), EventState=output_data.get("EventState"),
                             EventText=output_data.get("EventText"), EventType=output_data.get("EventType"),
                             Acknowledged=output_data.get("Acknowledged"), Active=output_data.get("Active"),
                             Category=output_data.get("Category"), Certainty=output_data.get("Certainty"),
                             ClearOnAcknowledge=output_data.get("ClearOnAcknowledge"),
                             Impact=output_data.get("Impact"), InMaintenance=output_data.get("InMaintenance"),
                             IsProblem=output_data.get("IsProblem"), IsRoot=output_data.get("IsRoot"),
                             PollingID=output_data.get("PollingID"), PollingState=output_data.get("PollingState"),
                             SourceDomainName=output_data.get("SourceDomainName"),
                             SourceEventType=output_data.get("SourceEventType"),
                             SourceInfo=output_data.get("SourceInfo"),
                             SourceSpecific=output_data.get("SourceSpecific"),
                             TroubleTicketID=output_data.get("TroubleTicketID"), Owner=output_data.get("Owner"),
                             ToolInfo=output_data.get("ToolInfo"), OccurrenceCount=output_data.get("OccurrenceCount"),
                             FirstNotifiedAt=output_data.get("FirstNotifiedAt"),
                             LastChangedAt=output_data.get("LastChangedAt"),
                             LastNotifiedAt=output_data.get("LastNotifiedAt"),
                             LastClearedAt=output_data.get("LastClearedAt"),
                             AcknowledgmentTime=output_data.get("AcknowledgmentTime"), tags=output_data.get("tags"),
                             properties=output_data.get("properties"))
            return event
        return None
