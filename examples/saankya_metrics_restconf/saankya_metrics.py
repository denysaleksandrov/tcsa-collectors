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
import os
import base64
from datetime import datetime
import time
import os
from vmware.tcsa.collector_sdk.collectors.batch_collector import BatchCollector
from vmware.tcsa.collector_sdk.models.metric import TCOMetric
import xml.etree.ElementTree as ET
from saankya_metrics_restconf.utils import GunicornApplication
from urllib.parse import urlparse
import paramiko


# Constants
thousand = 1000


class SaankyaMetrics(BatchCollector):
    ISO_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(self, logger, config) -> None:
        self._config = config
        self.event = multiprocessing.Event()
        self.app = Flask(__name__)
        super().__init__(logger, config)

    # override only if you want to change the default method execution sequence from collect->transform->publish
    def invoke(self, command: chr):
        self.collect()

    def collect(self):
        num_workers = 4

        # Define the endpoint for the POST request
        @self.app.route("/saankyametrics", methods=["POST"])
        def post_to_collect():
            try:
                # Extract the JSON body from the POST request
                data = request.get_json()
                event = data[0]["event"]
                notification_fields = event["notificationFields"]
                named_hash_maps = notification_fields["arrayOfNamedHashMap"]
                location = named_hash_maps[0]["hashMap"]["location"]
                print("location = ", location)
                # Use default daemon=False to stop threads gracefully in order to
                # release resources properly.
                t = threading.Thread(target=self._transform_message, args=(location, False))
                t.start()
                return "Data received successfully", 200
            except Exception as exc:
                error_message = "Error in processing data: %s[%s]" % (exc.__class__.__name__, exc)
                self._logger.exception(error_message)
                return error_message, 500

        def run_gunicorn():
            # Gunicorn configuration options
            gunicorn_options = {
                "bind": "0.0.0.0:8085",
                "workers": num_workers,
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

    def download_file(self, url):
        """Downloads a file from the given URL and saves it to the specified filename in /tmp"""
        try:
            parsed_url = urlparse(url)
            hostname, port = parsed_url.hostname, parsed_url.port or 22  # Default SSH port
            username = parsed_url.username
            password = parsed_url.password
            filepath = parsed_url.path
            filename = parsed_url.path.split("/")[-1]
            print("filename ==",filename)
            # Create an SFTP client
            transport = paramiko.Transport((hostname, port))
            transport.connect(username=username, password=password)
            sftp_client = paramiko.SFTPClient.from_transport(transport)
            print("connectd to server")
            # Download the file
            filepath_local = os.path.join("/tmp", filename)
            sftp_client.get(filepath, filepath_local)
            sftp_client.close()
            transport.close()
            print(f"File downloaded successfully: {filename}")
        except (paramiko.SSHException, FileNotFoundError) as e:
            print(f"Error downloading SFTP file: {e}")

    def delete_file(self, filename):
        """Deletes the specified file if it exists."""
        try:
            filepath = os.path.join("/tmp", filename)
            os.remove(filepath)
            print(f"File deleted successfully: {filename}")
        except FileNotFoundError:
            print(f"File '{filename}' not found.")

    def _transform_message(self, url,skip_publish=False):
        parsed_url = urlparse(url)
        filename = parsed_url.path.split("/")[-1]
        print("url = ",url)
        print("filename = ", filename)
        self.download_file(url)
        xml_content = ""
        filepath = os.path.join("/tmp", filename)
        try:
            with open(filepath,"rb") as f:
                xml_content = f.read()
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
            return None
        try:
            root = ET.fromstring(xml_content)
            # Namespace dictionary
            ns = {'ns': 'http://www.3gpp.org/ftp/specs/archive/28_series/28.532#measData'}
            # Extracting beginTime
            begin_time = root.find('.//ns:measData[@beginTime]', namespaces=ns).attrib['beginTime']
            print("time =",begin_time)
            # Extracting localDn
            local_dn = root.find('.//ns:measEntity', namespaces=ns).attrib['localDn']
            # Extracting fileSender
            file_sender_name = root.find('.//ns:fileSender', namespaces=ns).attrib['senderName']
            file_sender_type = root.find('.//ns:fileSender', namespaces=ns).attrib['senderType']
            # Extracting MeasInfo elements
            meas_info_elements = root.findall('.//ns:MeasInfo', namespaces=ns)
            # Extracting the vendor name
            vendor_name = root.find('.//ns:fileHeader',namespaces=ns).attrib['vendorName']
            print("Vendor Name: ", vendor_name)
            user_label = root.find('.//ns:measEntity', namespaces=ns).attrib['userLabel']
            print("user_label = ", user_label)
            # Initializing dictionary to store values
            data_dict = {'beginTime': begin_time, 'localDn': local_dn}
            # Iterate through MeasInfo elements
            for meas_info in meas_info_elements:
                # Iterate through measType elements
                for meas_type in meas_info.findall('.//ns:measType', namespaces=ns):
                    # Get the measurement type and its corresponding value
                    measurement = meas_type.text.strip()
                    p_value = meas_type.attrib['p']
                    meas_value_element = meas_info.find(f'.//ns:measValue/ns:r[@p="{p_value}"]', namespaces=ns)
                    if meas_value_element is not None:
                        value = float(meas_value_element.text.strip())
                        data_dict[measurement] = value
            print("data_dict = ",data_dict)
            # Convert string to datetime object
            dt = datetime.fromisoformat(begin_time)
            # Convert to epoch time (seconds since January 1, 1970)
            epoch_time = int(dt.timestamp())

            print("Epoch Time:", epoch_time)
            print("Extracted Data:",data_dict)
            output_data = {
                "type": "Netconf PM Collector",
                "metricType": "oran-pm-raw",
                "instance": local_dn,
                "timestamp": round(time.time()*1000),
                "processedTimestamp": round(time.time()*1000),
            }

            properties = {
                "dataSource": file_sender_name,
                "deviceName": user_label,
                "deviceType": file_sender_name,
                "entityType": vendor_name,
                "ip": vendor_name,
            }

            tags = {
                "technology": file_sender_name,
                "vendor": vendor_name,
            }

            output_data["properties"] = properties
            output_data["metrics"] = data_dict
            output_data["tags"] = tags
            tco_metric = TCOMetric(
                output_data.get("instance"),
                output_data.get("metricType"),
                output_data.get("timestamp"),
                output_data.get("processedTimestamp"),
                output_data.get("type"),
                output_data.get("metrics"),
                output_data.get("properties"),
                output_data.get("tags"),
            )
            self._logger.info("transformed metrics: %s", tco_metric.toJSON())
            self.delete_file(filename)
            if not skip_publish:
                self.publish(tco_metric)
        except Exception as e:
            self._logger.error("Exception in parsing the cml file  ", e)
            return None
        return  tco_metric
