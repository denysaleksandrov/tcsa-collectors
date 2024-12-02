class Event:
    def __init__(self, json_data):
        self.common_event_header = CommonEventHeader(**json_data["event"]["commonEventHeader"])
        self.fault_fields = FaultFields(**json_data["event"]["faultFields"])

class CommonEventHeader:
    def __init__(self, domain, version, eventId, eventName, sequence, priority, sourceId, reportingEntityName, timeZoneOffset, vesEventListenerVersion, sourceName, startEpochMicrosec, lastEpochMicrosec):
        self.domain = domain
        self.version = version
        self.eventId = eventId
        self.eventName = eventName
        self.sequence = sequence
        self.priority = priority
        self.sourceId = sourceId
        self.reportingEntityName = reportingEntityName
        self.timeZoneOffset = timeZoneOffset
        self.vesEventListenerVersion = vesEventListenerVersion
        self.sourceName = sourceName
        self.startEpochMicrosec = startEpochMicrosec
        self.lastEpochMicrosec = lastEpochMicrosec

class FaultFields:
    def __init__(self, faultFieldsVersion, eventSourceType, alarmInterfaceA, eventSeverity, alarmAdditionalInformation, vfStatus, alarmCondition, specificProblem):
        self.faultFieldsVersion = faultFieldsVersion
        self.eventSourceType = eventSourceType
        self.alarmInterfaceA = alarmInterfaceA
        self.eventSeverity = eventSeverity
        self.alarmAdditionalInformation = AlarmAdditionalInformation(**alarmAdditionalInformation)
        self.vfStatus = vfStatus
        self.alarmCondition = alarmCondition
        self.specificProblem = specificProblem

class AlarmAdditionalInformation:
    def __init__(self, alarmId, AlarmAction):
        self.alarmId = alarmId
        self.AlarmAction = AlarmAction  # Note the case sensitivity