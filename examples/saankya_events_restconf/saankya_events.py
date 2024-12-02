"""
# Copyright (c) 2021-2023 VMware, Inc. All rights reserved.
# VMware Confidential
"""
import json
import multiprocessing
import sys
from flask import Flask, request
from multiprocessing import Process
import threading
from vmware.tcsa.collector_sdk.collectors.batch_collector import BatchCollector
from saankya_events_restconf.utils import GunicornApplication
from vmware.tcsa.collector_sdk.models.event import TCOEvent
from saankya_events_restconf.Event import Event
import time

class SaankyaEvents(BatchCollector):
    def __init__(self, logger, config) -> None:
        self._config = config
        self.event = multiprocessing.Event()
        self.app = Flask(__name__)
        super().__init__(logger, config)

    # override only if you want to change the default method execution sequence from collect->transform->publish
    def invoke(self, command: chr):
        self.collect()

    def collect(self):
        # Define the endpoint for the POST request
        @self.app.route("/saankyaevents", methods=["POST"])
        def post_to_collect():
            try:
                # Extract the JSON body from the POST request
                data = request.get_json()
                json_string = json.dumps(data)

                # Use default daemon=False to stop threads gracefully in order to
                # release resources properly.
                t = threading.Thread(target=self._transform_message, args=(json_string, False))
                t.start()
                return "Data received successfully", 200
            except Exception as exc:
                error_message = "Error in processing data: %s[%s]" % (exc.__class__.__name__, exc)
                self._logger.exception(error_message)
                return error_message, 500

        def run_gunicorn():
            # Gunicorn configuration options
            gunicorn_options = {
                "bind": "0.0.0.0:8085" ,
                "workers": 4,
            }
            # Start the Flask app with Gunicorn
            GunicornApplication(self.app, gunicorn_options).run()

        try:
            p = Process(target=run_gunicorn, daemon=True, args=())
            p.start()
            self._logger.info("Starting Gunicorn server in worker #%s", p.pid)

            while True:
                if self.event.is_set():
                    self._logger.info("Exiting all child processes..")
                    p.terminate()
                    sys.exit(1)

        except Exception as e:
            self._logger.error("Exception in process ", e)

    def transform(self):
        pass

    def _transform_message(self, data, skip_publish=False):
        try:
            print("JSON LOADS..", data)
            events = json.loads(data)
            eventdata = Event(events[0])
            faultId = eventdata.common_event_header.sourceId
            faultSource = eventdata.fault_fields.eventSourceType
            faultSeverity = eventdata.common_event_header.priority
            affObj = eventdata.fault_fields.alarmInterfaceA
            faultText = eventdata.fault_fields.specificProblem
            eventTime = eventdata.common_event_header.startEpochMicrosec
            isCleared = eventdata.fault_fields.alarmAdditionalInformation.AlarmAction
            eventName = eventdata.common_event_header.eventName
            self.publishEvent(faultId, eventTime, isCleared, faultSeverity, faultSource, faultText, affObj,eventName )
        except Exception as e:
            self._logger.error("Exception in parsing the incoming event JSON ", e)

    def publishEvent(self, fault_id, eventTime,  is_cleared, fault_severity, fault_source, fault_text, affected_objects,eventName):
        event = TCOEvent()
        event.Description = event.EventText = event.EventDisplayName = event.InstanceDisplayName = event.SourceInfo = fault_text
        event.Timestamp = event.LastChangedAt = event.LastClearedAt = event.LastNotifiedAt = event.FirstNotifiedAt = eventTime
        event.ProcessedTimeStamp = event.AcknowledgmentTime = round(time.time() * 1000)
        event.ClassName = event.ElementClassName = affected_objects
        event.DisplayName = event.ElementName = event.InstanceName= fault_source
        event.State = event.EventState = "INACTIVE" if is_cleared == "CLEAR" else "ACTIVE"
        severity_mapping = {"CRITICAL":"Critical","MAJOR":"Major","WARNING":"Minor","INFO":"Normal","NORMAL":"NORMAL"}
        event.SourceSpecific = fault_severity
        event.EventName = event.ClassDisplayName = eventName
        event.Severity = event.Impact = 1
        event.Source = "saankya-events-collector"
        event.Category = "PERFORMANCE"
        event.Certainty = event.PollingID =  fault_id
        event.PollingState = "STATE"
        event.EventType = event.Name =fault_source
        event.SourceEventType = event.SourceDomainName = fault_source
        event.InMaintenance = event.IsRoot = event.IsProblem = event.Active = event.ClearOnAcknowledge =True
        tagsDict = {"customer":"cisco","location":"router"}
        event.tags = tagsDict
        self.publish(event)
