import paramiko, base64
from vmware.tcsa.collector_sdk.collectors.stream_collector import StreamCollector
from vmware.tcsa.collector_sdk.models.event import TCOEvent
from netconf_collector.topocache import TopoCache
from ncclient import manager
import os
import threading
import time
from datetime import datetime


class NetConfCollector(StreamCollector):

    def __init__(self, logger, config):
        self._config = config
        if self._config.connect.gateway.enabled:
            pkey_filename = "/app/config/{}.pkey".format(self._config.connect.gateway.host)
            pkey_fd = os.fdopen(os.open(pkey_filename, os.O_WRONLY | os.O_CREAT, 0o600), "w")
            pkey_fd.write(base64.b64decode(self._config.connect.gateway.key).decode())
            pkey_fd.close()
        self.connect()
        super(StreamCollector, self).__init__(logger, config)
        self._topoCache = TopoCache(self._session, self._logger, self._config)
        self._topoCache.start()
        t = threading.Thread(target=self.reconnect, args=())
        t.start()

    def connect(self):
        self._proxy_sock = None
        if self._config.connect.gateway.enabled:
            pkey_filename = "{}.pkey".format(self._config.connect.gateway.host)
            proxy_cmd = "ssh -oServerAliveInterval=3600 -oStrictHostKeyChecking=no -q -W {}:{} {}@{} -i {}".format(
                self._config.connect.host,
                self._config.connect.port,
                self._config.connect.gateway.username,
                self._config.connect.gateway.host,
                pkey_filename)
            self._proxy_sock = paramiko.ProxyCommand(proxy_cmd)
            self._proxy_sock.settimeout(10)
        self._session = manager.connect_ssh(host=self._config.connect.host, port=self._config.connect.port,
                                            username=self._config.connect.username,
                                            password=self._config.connect.password, hostkey_verify=False, sock=self._proxy_sock, manager_params={"timeout": 120}, keepalive=True)

    # override only if you want to change the default method execution sequence from collect->transform->publish
    def invoke(self, command: chr):
        self.collect()

    def collect(self):
        # self._logger.info("Server Capabilities")
        # for cap in self._session.server_capabilities:
        #     self._logger.info(cap)
        # self._logger.info("Client Capabilities")
        # for cap in self._session.client_capabilities:
        #     self._logger.info(cap)
        # while not self._topoCache.isReady():
        #     time.sleep(2)
        # self.getCurrentProblems()
        self._session.create_subscription()
        self._logger.info(
            '#%s - Starting  the subscriber topic=%s', os.getpid(), "testtopic")
        while True:
            self._logger.info('#%s - Waiting for message...', os.getpid())
            try:
                msg = self._session.take_notification().notification_ele
                # self._logger.debug("Notification received", msg.text)
                if msg is None:
                    continue
                self._transform_message(msg)
            except Exception:
                self._logger.exception('#%s - Received exception.', os.getpid())
        # Get the current Problem List and emit notifications

    def reconnect(self):
        self._logger.info("Reconnect thread called")
        while True:
            try:
                # Send ok. and handle the exception to reconnect.
                # self._session.get
                if (not self._session.connected):
                    self._logger.info("connection lost. Retrying...")
                    self._proxy_sock.close()
                    self.connect()
                    self._proxy_sock.settimeout(10)
                    self._topoCache.setSession(self._session);
                    self.getCurrentProblems()
                    self._session.create_subscription()
                    self._logger.info("Reconnect successful")
                time.sleep(10)
            except Exception as e:
                self._logger.info("Exception received and try to reconnect %s", e)
                time.sleep(10)

    def transform(self):
        pass

    def getCurrentProblems(self):
        try:
            self._logger.debug("Start processing the current problem list");
            filterExp = "<equipment-pac></equipment-pac>"
            data = self._session.get(filter=("subtree", filterExp)).data_ele
            for elem in data.getchildren():
                for innerelem in elem.getchildren():
                    ns="{urn:ietf:params:xml:ns:netconf:base:1.0}"
                    if innerelem.tag == "equipment":
                        object_id = innerelem.text
                        ns=""
                    elif innerelem.tag == ns + "equipment":
                        object_id = innerelem.text
                    self._logger.debug("Object id is " + object_id)
                    if innerelem.tag == ns + "equipment-current-problems":
                        for curreProblem in innerelem.getchildren():
                            problem=curreProblem.find(".//" + ns+ "problem-name").text
                            severity = curreProblem.find(".//" + ns + "problem-severity").text
                            ts = curreProblem.find(".//" + ns + "time-stamp").text
                            eventTime=ts
                            self._logger.debug("Raising current problem %s %s  %s %s %s", object_id, problem, severity, ts, eventTime)
                            self.publishEvent(problem, eventTime, ts, object_id, severity)
        except Exception as e:
            self._logger.debug("Exception received %s", e)


    def publishEvent(self, problem, eventTime, ts, object_id, severity ):
        event = TCOEvent()
        event.Name = event.EventName = event.DisplayName = problem
        event.EventText = event.Description = problem
        event.Timestamp = datetime.strptime(eventTime, '%Y-%m-%dT%H:%M:%SZ').timestamp() * 1000
        event.ProcessedTimeStamp = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').timestamp() * 1000
        event.ElementName = event.InstanceDisplayName = event.InstanceName = self._topoCache.getInstName(object_id)
        event.ElementClassName = event.ClassDisplayName = event.ClassName = self._topoCache.getType(object_id)
        event.State = event.EventState = "INACTIVE" if severity == "non-alarmed" else "ACTIVE"
        event.Severity = "Critical" if severity != "non-alarmed" else "Major"
        event.Source = "netconf-notification-collector"
        self.publish(event)

    def _transform_message(self, msg):
        # apply custom transform on collected object
        self._logger.debug('started transform on data %s', msg)
        # self._logger.info(
        #    '#%sT%s - Received message: %s', os.getpid(), threading.get_ident(), msg.value().decode('utf-8'))
        notif_ns = "{urn:ietf:params:xml:ns:netconf:notification:1.0}"
        ns = "{urn:onf:params:xml:ns:yang:microwave-model}"

        for elem in msg.getchildren():
            if elem.tag == notif_ns + "eventTime":
                eventTime = elem.text
                continue
            for pnotif_elem in elem.getchildren():
                if pnotif_elem.tag == ns + "counter":
                    counter = pnotif_elem.text
                if pnotif_elem.tag == ns + "time-stamp":
                    ts = pnotif_elem.text
                if pnotif_elem.tag == ns + "problem":
                    problem = pnotif_elem.text
                if pnotif_elem.tag == ns + "severity":
                    severity = pnotif_elem.text
                if pnotif_elem.tag == ns + "object-id-ref":
                    object_id = pnotif_elem.text
        self._logger.debug(" eventTime %s", eventTime)
        self._logger.debug(" counter %s", counter)
        self._logger.debug(" time-stampe %s", ts)
        self._logger.debug(" problem %s", problem)
        self._logger.debug(" severity %s", severity)
        self._logger.debug(" object-id-ref %s", object_id)
        self.publishEvent(problem, eventTime, ts, object_id, severity)
        # self._logger.info("transform completed", output_data)