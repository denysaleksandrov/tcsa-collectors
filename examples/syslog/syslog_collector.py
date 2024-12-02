import time
import socket
import threading
import re
import os
import paramiko
import hashlib
import requests
import logging
from collections import deque
from datetime import datetime

from vmware.tcsa.collector_sdk.collectors.stream_collector import StreamCollector
from vmware.tcsa.collector_sdk.models.event import TCOEvent
from vmware.tcsa.collector_sdk.stats.stats import PROCESSED_COUNT


class SyslogCollector(StreamCollector):
    severity_map = {
        "1": "Critical",
        "2": "Major",
        "3": "Minor",
        "4": "Unknown",
        "5": "Normal",
        "6": "Info"
    }

    category_map = {
        "AVAILABILITY": "18",
        "PERFORMANCE": "19",
        "CAPACITY": "20",
        "COMPLIANCE": "21",
        "CONFIGURATION": "22",
    }

    def __init__(self, logger, config: dict) -> None:
        self.ssh_client = None
        self.collected_data = None
        self.origin = None
        self._config = config
        self.shutdown_event = threading.Event()
        self.message_queue = deque()
        self.MAX_QUEUE_SIZE = 10000
        self.api_url = "http://collector-manager:12375/dcc/v1"
        self.collector_name = os.environ.get("INSTANCE_NAME", "default-syslog-collector")

        self.received_messages = PROCESSED_COUNT.labels("received")
        self.dropped_messages = PROCESSED_COUNT.labels("dropped")
        self.processed_messages = PROCESSED_COUNT.labels("processed")
        self.received_messages.set(0)
        self.dropped_messages.set(0)
        self.processed_messages.set(0)
        self.counter_lock = threading.Lock()

        self.is_initial_startup = True

        super().__init__(logger, config)

    # override only if you want to change the default method execution sequence from collect->transform->publish
    def invoke(self, command: chr):
        self.collect()

    def collect(self):
        self._logger.info("Started collecting syslog messages through exposed port")
        # Sample Syslog Message: *Feb 14 12:02:38: %LINK-5-CHANGED: Interface FastEthernet0/1, changed state to administratively down
        is_query_mode = self._config.mode.mode_type
        if is_query_mode.lower() == "query":
            self.initialize_query_mode()
            self.query_mode()
        else:
            self.listen_mode()

    def listen_mode(self):
        self._logger.info("Collecting the Syslog via Listen Mode")
        # Get the service port from PortBindings or set default port if not configured
        service_port = self._config.mode.listen_settings.PortBindings.port or 2046
        # Define the UDP server address
        UDP_IP = "0.0.0.0"
        try:
            # Create a UDP socket
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                # Bind the socket to the address and service port
                if service_port:
                    sock.bind((UDP_IP, service_port))
                    self._logger.info("UDP server is listening on port = %s", service_port)
                else:
                    self._logger.info("No service port provided. Listening on default port 2046.")
                    sock.bind((UDP_IP, 2046))

                # Start a thread for processing messages
                process_thread = threading.Thread(target=self.process_listen_mode_messages)
                process_thread.start()

                # Listen for incoming messages
                while not self.shutdown_event.is_set():
                    data, addr = sock.recvfrom(65535)  # Buffer size
                    self.origin = addr[0]
                    self.message_queue.appendleft(data)

        except Exception as e:
            self._logger.error(f"Error occurred while listening on the port in listen_mode : {e}")
            with self.counter_lock:
                self.dropped_messages.inc()
        finally:
            self.shutdown_event.set()

    def query_mode(self):
        self._logger.info("Collecting the Syslog via Query Mode")

        def initialize():
            path = self._config.mode.query_settings.log_directory
            last_offset = self.load_last_offset(initial_startup=self.is_initial_startup)
            if last_offset is None:
                self.add_last_offset(last_offset)
                self.is_initial_startup = False
            return path, last_offset, last_offset

        def execute_command(cmd):
            stdin, out, stderr = self.ssh_client.exec_command(cmd)
            return out

        def process_lines(out, last_offset, processed_offset):
            new_msgs = False
            for line in out:
                msg_hash = hashlib.sha256(line.encode()).hexdigest()
                if msg_hash == last_offset:
                    # Latest message matched with the existing message in the logs.
                    break

                if not new_msgs:
                    last_offset = msg_hash

                if msg_hash == processed_offset:
                    self.process_query_mode_messages()
                    break
                else:
                    if len(self.message_queue) >= self.MAX_QUEUE_SIZE:
                        self.message_queue.pop()
                    self.message_queue.appendleft(line)
                    new_msgs = True
            return last_offset, new_msgs

        def handle_no_new_msgs(new_msgs):
            if not new_msgs and not self.message_queue:
                time.sleep(10)
            elif self.message_queue:
                self.process_query_mode_messages()

        def cleanup():
            if self.ssh_client:
                self.ssh_client.close()
            self.shutdown_event.set()

        try:
            syslog_path, last_offset_hash, processed_offset_hash = initialize()
            while not self.shutdown_event.is_set():
                command = f"tac {syslog_path}"
                stdout = execute_command(command)
                last_offset_hash, new_messages = process_lines(stdout, last_offset_hash, processed_offset_hash)

                if processed_offset_hash != last_offset_hash:
                    processed_offset_hash = last_offset_hash
                    self.update_last_offset(last_offset_hash)

                handle_no_new_msgs(new_messages)

        except Exception as e:
            self._logger.error(f"Error occurred in the query_mode: {e}")
            with self.counter_lock:
                self.dropped_messages.inc()

        finally:
            cleanup()

    def initialize_query_mode(self):
        self.connect_ssh()

    def connect_ssh(self):
        # Set the logging level for the paramiko.transport and urllib3.connectionpool logger to CRITICAL
        logging.getLogger("paramiko.transport").setLevel(logging.CRITICAL)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.CRITICAL)
        self.ssh_client = paramiko.SSHClient()
        self.origin = self._config.mode.query_settings.host
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(self._config.mode.query_settings.host, username=self._config.mode.query_settings.username,
                                password=self._config.mode.query_settings.password)

    def load_last_offset(self, initial_startup=False):
        url = f"{self.api_url}/syslog-collectors/{self.collector_name}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            last_offset_hash = data.get("latest_log_offset")
            if last_offset_hash:
                return last_offset_hash
            else:
                return None
        except requests.exceptions.RequestException as e:
            if not initial_startup:
                self._logger.error(f"Failed to retrieve last offset via API: {e}")
            return None

    def add_last_offset(self, offset_hash):
        url = f"{self.api_url}/syslog-collectors"
        payload = {
            "name": self.collector_name,
            "latest_log_offset": offset_hash
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Error occurred while adding last offset hash via API: {e}")

    def update_last_offset(self, offset_hash):
        url = f"{self.api_url}/syslog-collectors"
        payload = {
            "name": self.collector_name,
            "latest_log_offset": offset_hash
        }
        try:
            response = requests.put(url, json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Error occurred while updating last offset hash via API: {e}")

    def process_listen_mode_messages(self):
        while not self.shutdown_event.is_set():
            if self.message_queue:
                self.process_messages()

    def process_query_mode_messages(self):
        while self.message_queue:
            self.process_messages()

    def process_messages(self):
        message = self.message_queue.pop()
        try:
            # Process the message
            self.process_message(message.strip())
            # Avoid busy-waiting by sleeping briefly
            time.sleep(0.1)
        except Exception as e:
            self._logger.error(f"Error occurred while processing messages: {e}")
            with self.counter_lock:
                self.dropped_messages.inc()

    def process_message(self, data):
        try:
            # Check if data needs to be decoded
            if isinstance(data, bytes):
                # Decode and store received data
                self.collected_data = data.decode()
            else:
                self.collected_data = data
            # Process the received data using self.transform_message()
            self._logger.debug("syslog collected_data = %s ", self.collected_data)
            with self.counter_lock:
                self.received_messages.inc()

            self._transformed_data = self.transform_message()

        except Exception as e:
            self._logger.error(f"Error occurred while processing message: {e}")
            with self.counter_lock:
                self.dropped_messages.inc()

    def transform_message(self):
        self._logger.debug("syslog started transform()")
        collected_data = self.collected_data

        if collected_data is not None:
            # apply custom transform on collected object
            output_data = {}

            # Access input_mapper
            input_mapper = vars(self._config.notification_attributes)
            extracted_data = self.extract_values(collected_data, input_mapper)

            user_defined_fields = vars(self._config.user_defined_fields.settings)
            user_defined_extracted_data = self.extract_values(collected_data, user_defined_fields)

            class_name = extracted_data.get("className")
            instance_name = extracted_data.get("instanceName")
            event_name = extracted_data.get("eventName")

            # return if the notification any of the class_name, event_name or instance_name is empty.
            if not class_name or not instance_name or not event_name:
                with self.counter_lock:
                    self.dropped_messages.inc()
                return None
            notification_name = class_name + "_" + instance_name + "_" + event_name

            event_state = extracted_data.get("eventState") if extracted_data.get("eventState") else "ACTIVE"

            output_data['InstanceName'] = instance_name
            output_data['Source'] = extracted_data.get("source")
            output_data['Timestamp'] = extracted_data.get("timestamp")  # round(time.time())
            output_data['ProcessedTimeStamp'] = extracted_data.get("timestamp")
            output_data['Name'] = notification_name
            output_data['State'] = event_state

            # Get the severity number from extracted data
            severity_number = extracted_data.get("severity")
            # Set the severity text in output data
            output_data["Severity"] = self.severity_map.get(severity_number, "Unknown")

            output_data["Category"] = self.category_map.get((extracted_data.get("category")), "18")  # Default category is set to AVAILABILITY
            output_data["EventState"] = event_state
            output_data["ElementName"] = ""
            output_data["Owner"] = ""
            output_data["EventText"] = extracted_data.get("eventText")
            output_data["EventName"] = event_name
            output_data["DisplayName"] = notification_name
            output_data["EventDisplayName"] = event_name
            output_data["ClassDisplayName"] = class_name
            output_data["InstanceDisplayName"] = notification_name
            output_data[
                "SourceEventType"] = "15"  # SourceEventType has an Enum mapping in Smarts code ["15", "APPLICATION"], ["16", "VIRTUALIZATION/HYPERVISOR"], ["17", "HARDWARE"], ["18", "STORAGE"], ["19", "NETWORK"], Setting it default to APPLICATION for SysLog
            output_data["ClassName"] = class_name
            output_data["ElementClassName"] = ""
            output_data["EventType"] = extracted_data.get("eventType")
            output_data["Acknowledged"] = False
            output_data["Active"] = True
            output_data["Certainty"] = 1.234
            output_data["ClearOnAcknowledge"] = True
            output_data["Impact"] = 0
            output_data["IsProblem"] = True
            output_data["IsRoot"] = True
            output_data["PollingID"] = 1
            output_data["PollingState"] = ""
            output_data["SourceDomainName"] = extracted_data.get("source")
            output_data["SourceInfo"] = ""
            output_data["SourceSpecific"] = ""
            output_data["TroubleTicketID"] = ""
            output_data["ToolInfo"] = ""
            output_data["OccurrenceCount"] = 1
            output_data["FirstNotifiedAt"] = round(time.time())
            output_data["LastChangedAt"] = round(time.time())
            output_data["LastNotifiedAt"] = round(time.time())
            output_data["LastClearedAt"] = round(time.time())
            output_data["AcknowledgmentTime"] = 30
            output_data["UserDefined1"] = user_defined_extracted_data.get("userDefined1")
            output_data["UserDefined2"] = user_defined_extracted_data.get("userDefined2")
            output_data["UserDefined3"] = user_defined_extracted_data.get("userDefined3")
            output_data["UserDefined4"] = user_defined_extracted_data.get("userDefined4")
            output_data["UserDefined5"] = user_defined_extracted_data.get("userDefined5")
            output_data["UserDefined6"] = user_defined_extracted_data.get("userDefined6")
            output_data["UserDefined7"] = user_defined_extracted_data.get("userDefined7")
            output_data["UserDefined8"] = user_defined_extracted_data.get("userDefined8")
            output_data["UserDefined9"] = user_defined_extracted_data.get("userDefined9")
            output_data["UserDefined10"] = user_defined_extracted_data.get("userDefined10")
            output_data["UserDefined11"] = user_defined_extracted_data.get("userDefined11")
            output_data["UserDefined12"] = user_defined_extracted_data.get("userDefined12")
            output_data["UserDefined13"] = user_defined_extracted_data.get("userDefined13")
            output_data["UserDefined14"] = user_defined_extracted_data.get("userDefined14")
            output_data["UserDefined15"] = user_defined_extracted_data.get("userDefined15")
            output_data["UserDefined16"] = user_defined_extracted_data.get("userDefined16")
            output_data["UserDefined17"] = user_defined_extracted_data.get("userDefined17")
            output_data["UserDefined18"] = user_defined_extracted_data.get("userDefined18")
            output_data["UserDefined19"] = user_defined_extracted_data.get("userDefined19")
            output_data["UserDefined20"] = user_defined_extracted_data.get("userDefined20")
            output_data["tags"] = {}
            output_data["properties"] = {}
            output_data["InMaintenance"] = True

            event = TCOEvent(Source=output_data.get("Source"),
                             Name=output_data.get("Name"),
                             InstanceName=output_data.get("InstanceName"),
                             State=output_data.get("State"),
                             Severity=output_data.get("Severity"),
                             ProcessedTimeStamp=output_data.get("ProcessedTimeStamp"),
                             Timestamp=output_data.get("Timestamp"),
                             DisplayName=output_data.get("DisplayName"),
                             EventDisplayName=output_data.get("EventDisplayName"),
                             ClassName=output_data.get("ClassName"),
                             ClassDisplayName=output_data.get("ClassDisplayName"),
                             InstanceDisplayName=output_data.get(
                                 "InstanceDisplayName"),
                             ElementClassName=output_data.get("ElementClassName"),
                             ElementName=output_data.get("ElementName"),
                             EventName=output_data.get("EventName"),
                             EventState=output_data.get("EventState"),
                             EventText=output_data.get("EventText"),
                             EventType=output_data.get("EventType"),
                             Acknowledged=output_data.get("Acknowledged"),
                             Active=output_data.get("Active"),
                             Category=output_data.get("Category"),
                             Certainty=output_data.get("Certainty"),
                             ClearOnAcknowledge=output_data.get("ClearOnAcknowledge"),
                             Impact=output_data.get("Impact"),
                             InMaintenance=output_data.get("InMaintenance"),
                             IsProblem=output_data.get("IsProblem"),
                             IsRoot=output_data.get("IsRoot"),
                             PollingID=output_data.get("PollingID"),
                             PollingState=output_data.get("PollingState"),
                             SourceDomainName=output_data.get("SourceDomainName"),
                             SourceEventType=output_data.get("SourceEventType"),
                             SourceInfo=output_data.get("SourceInfo"),
                             SourceSpecific=output_data.get("SourceSpecific"),
                             TroubleTicketID=output_data.get("TroubleTicketID"),
                             Owner=output_data.get("Owner"),
                             ToolInfo=output_data.get("ToolInfo"),
                             OccurrenceCount=output_data.get("OccurrenceCount"),
                             FirstNotifiedAt=output_data.get("FirstNotifiedAt"),
                             LastChangedAt=output_data.get("LastChangedAt"),
                             LastNotifiedAt=output_data.get("LastNotifiedAt"),
                             LastClearedAt=output_data.get("LastClearedAt"),
                             AcknowledgmentTime=output_data.get("AcknowledgmentTime"),
                             UserDefined1=output_data.get("UserDefined1"),
                             UserDefined2=output_data.get("UserDefined2"),
                             UserDefined3=output_data.get("UserDefined3"),
                             UserDefined4=output_data.get("UserDefined4"),
                             UserDefined5=output_data.get("UserDefined5"),
                             UserDefined6=output_data.get("UserDefined6"),
                             UserDefined7=output_data.get("UserDefined7"),
                             UserDefined8=output_data.get("UserDefined8"),
                             UserDefined9=output_data.get("UserDefined9"),
                             UserDefined10=output_data.get("UserDefined10"),
                             UserDefined11=output_data.get("UserDefined11"),
                             UserDefined12=output_data.get("UserDefined12"),
                             UserDefined13=output_data.get("UserDefined13"),
                             UserDefined14=output_data.get("UserDefined14"),
                             UserDefined15=output_data.get("UserDefined15"),
                             UserDefined16=output_data.get("UserDefined16"),
                             UserDefined17=output_data.get("UserDefined17"),
                             UserDefined18=output_data.get("UserDefined18"),
                             UserDefined19=output_data.get("UserDefined19"),
                             UserDefined20=output_data.get("UserDefined20"),
                             tags=output_data.get("tags"),
                             properties=output_data.get("properties"))

            self.publish(event)

            with self.counter_lock:
                self.processed_messages.inc()

            return event

        return None

    def extract_values(self, syslog_message, regex_config):
        extracted_data = {}
        try:
            for key, regex_pattern in regex_config.items():
                if self._is_valid_key(key) and isinstance(regex_pattern, str):
                    extracted_data[key] = self._apply_regex(regex_pattern, syslog_message, key)

        except Exception as e:
            logging.error(f"Error occurred while extracting values: {e}")

        return extracted_data

    def _apply_regex(self, regex_pattern, syslog_message, key):
        try:
            if regex_pattern.startswith("$"):
                # Handle special cases
                if "(" in regex_pattern and ")" in regex_pattern:
                    # It's a method
                    method_name, method_args = self.extract_method_and_args(regex_pattern)
                    method = getattr(self, method_name, None)
                    if method:
                        return self.higher(method, syslog_message, *method_args)
                else:
                    # It's a variable
                    if regex_pattern == "$IP":
                        return self.origin
                    # Add more variable cases as needed
            else:
                # Handle regular regex pattern
                if self.is_valid_regex(regex_pattern):
                    match = re.search(regex_pattern, syslog_message)
                    if match:
                        return match.group(1) if key != "message" else match.group(0).lstrip(":").strip()
                else:
                    # If no valid regular expression is specified, maintain the default value as provided.
                    return regex_pattern
        except Exception as e:
            logging.error(f"Error occurred while applying regex {regex_pattern} : {e}")
        return None

    @staticmethod
    def extract_method_and_args(method_call):
        method_name = method_call.split("(")[0][1:]
        args_str = method_call.split("(", 1)[1].rsplit(")", 1)[0]
        args = re.findall(r'"(.*?)(?<!\\)"', args_str)
        args = [arg.replace('\\"', '"') for arg in args]  # Handle escaped quotes within arguments
        return method_name, args

    @staticmethod
    def higher(fnc, *args):
        try:
            return fnc(*args)
        except Exception as e:
            logging.error(f"Error occurred while calling the function {fnc.__name__}: {e}")
            return None

    @staticmethod
    def transform_date(date_str, custom_format='YYYY-MM-DDTHH:mm:SS.FZ'):
        # Convert custom format to strftime format
        strftime_format = SyslogCollector.custom_to_strftime_format(custom_format)

        # Generate regex from the strftime format
        date_pattern = SyslogCollector.generate_regex_from_format(strftime_format)
        # Find date string in the syslog message
        found_date_str = SyslogCollector.find_date_in_syslog(date_str, date_pattern)
        if found_date_str is None:
            return None

        # Convert date string to epoch time
        try:
            date_obj = datetime.strptime(found_date_str, strftime_format)
            epoch_time = int(date_obj.timestamp())
            return epoch_time
        except ValueError as ve:
            logging.error(
                f"Error occurred while transforming date {found_date_str} in the format {strftime_format}: {ve}")
            return None

    @staticmethod
    def custom_to_strftime_format(custom_format):
        replacements = {
            'YYYY': '%Y',
            'YY': '%y',
            'MM': '%m',
            'DD': '%d',
            'HH': '%H',
            'mm': '%M',
            'SS': '%S',
            'F': '%f'
        }

        strftime_format = custom_format
        for key, value in replacements.items():
            strftime_format = strftime_format.replace(key, value)

        return strftime_format

    @staticmethod
    def generate_regex_from_format(date_format):
        replacements = {
            '%Y': r'\d{4}',
            '%y': r'\d{2}',
            '%m': r'\d{2}',
            '%d': r'\d{2}',
            '%H': r'\d{2}',
            '%M': r'\d{2}',
            '%S': r'\d{2}',
            '%f': r'\d{1,6}',
            '%z': r'(?:\+|-)\d{2}(?::?\d{2})?',
            '%Z': r'(?:UTC|GMT|Z|[\+-]\d{2}(?::?\d{2})?)',
            '-': r'-',
            ':': r':',
            'T': r'T',
            '.': r'\.'
        }
        regex = re.escape(date_format)
        for key, value in replacements.items():
            regex = regex.replace(re.escape(key), value)

        return regex

    @staticmethod
    def find_date_in_syslog(syslog_message, date_pattern):
        match = re.search(date_pattern, syslog_message)
        if match:
            return match.group(0)
        else:
            logging.debug(f"No date found in the syslog message: {syslog_message}")
            return None

    @staticmethod
    def set_on_match(syslog_message, *args):
        try:
            for i in range(0, len(args), 2):
                regex = args[i]
                value_to_match = args[i + 1]
                if re.search(regex, syslog_message):
                    return value_to_match
            return "ACTIVE"
        except Exception as e:
            logging.error(f"Error occurred while applying set_on_match: {e}")
            return "ACTIVE"

    @staticmethod
    def _is_valid_key(key):
        return not key.startswith('get_')

    @staticmethod
    def is_valid_regex(pattern):
        try:
            re.compile(pattern)
            # Check if pattern contains common regex special characters
            if not re.search(r'[\.\*\+\?\|\(\)\[\]\{\}]', pattern):
                return False
            return True
        except re.error:
            return False
