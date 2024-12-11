#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import time
import logging
import threading
import multiprocessing

from flask import Flask, request
from multiprocessing import Process
from utils import GunicornApplication

app = Flask(__name__)
logger = logging.getLogger("Logger")

@app.route("/events", methods=["GET"])
def get_events():
    output_data = {}
    output_data['InstanceName'] = "pod"
    output_data['Source'] = "RESTEVENTS"
    output_data['Timestamp'] = round(time.time() * 1000)
    output_data['ProcessedTimeStamp'] = round(time.time() * 1000)
    output_data['Name'] = "test_k8s_pod"
    output_data['State'] = "Running"
    output_data["Severity"] = "3"
    output_data["Category"] = "Resource"
    output_data["EventState"] = "Running"
    output_data["ElementName"] = "test_k8s_name"
    output_data["Owner"] = "RESTAPI"
    output_data["EventText"] = "Pod is running"
    output_data["EventName"] = "TestEvent"
    output_data["DisplayName"] = "pod"
    output_data["EventDisplayName"] = "pod"
    output_data["ClassDisplayName"] = "pod"
    output_data["InstanceDisplayName"] = "pod"
    output_data["SourceEventType"] = "EVENTS"
    output_data["ClassName"] = "pod"
    output_data["ElementClassName"] = "pod"
    output_data["EventType"] = "DURABLE"
    output_data["Acknowledged"] = False
    output_data["Active"] = False
    output_data["Certainty"] = 100
    output_data["ClearOnAcknowledge"] = True
    output_data["Impact"] = 0
    output_data["IsProblem"] = True
    output_data["IsRoot"] = True
    output_data["PollingID"] = "14"
    output_data["PollingState"] = "Running"
    output_data["SourceDomainName"] = "pod"
    output_data["SourceInfo"] = "1.28.13"
    output_data["SourceSpecific"] = "1.28.13"
    output_data["TroubleTicketID"] = "8767685"
    output_data["ToolInfo"] = "1.28.13"
    output_data["OccurrenceCount"] = 2
    output_data["FirstNotifiedAt"] = round(time.time() * 1000)
    output_data["LastChangedAt"] = round(time.time() * 1000)
    output_data["LastNotifiedAt"] = round(time.time() * 1000)
    output_data["LastClearedAt"] = round(time.time() * 1000)
    output_data["AcknowledgmentTime"] = 30
    output_data["tags"] = {
        "Region": "east-1a"
    }
    output_data["properties"] = {}
    output_data["InMaintenance"] = True

    return json.dumps(output_data), 200, {'ContentType':'application/json'}

@app.route("/metrics", methods=["GET"])
def get_metrics():
    metric = {
        "instance": "10.192.108.3:Border-T0:edge01-uplink2",
        "metricType": "rx_malformed_dropped_packets",
        "metrics": {
            "sample": 678
        },
        "processedTimestamp": round(time.time() * 1000),
        "properties": {
            "dataSource": "10.192.108.3",
            "deviceName": "Border-T0",
            "deviceType": "nsxEdge",
            "entityName": "edge01-uplink2",
            "entityType": "Interface",
            "ip": "10.192.108.3"
        },
        "tags": {
            "deviceName": "Border-T0",
            "hostname": "Border-T0"
        },
        "timestamp": round(time.time() * 1000),
        "type": "Rest-Custom-Collector"
    }
    return json.dumps(metric), 200, {'ContentType':'application/json'}

def run_gunicorn():
    # Gunicorn configuration options
    gunicorn_options = {
        "bind": "0.0.0.0:8085" ,
        "workers": 4,
    }
    # Start the Flask app with Gunicorn
    GunicornApplication(app, gunicorn_options).run()

def main():
    event = multiprocessing.Event()
    try:
        p = Process(target=run_gunicorn, daemon=True, args=())
        p.start()
        logger.info(f"Starting Gunicorn server in worker {p.pid}")

        while True:
            if event.is_set():
                logger.info("Exiting all child processes..")
                p.terminate()
                sys.exit(1)
    except Exception as e:
        logger.error("Exception in process ", e)


if __name__ == '__main__':
    main()
