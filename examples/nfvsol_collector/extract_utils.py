from vmware.tcsa.collector_sdk.models.topology_models.storage.central_unit_control_plane import CentralUnitControlPlane
from vmware.tcsa.collector_sdk.models.topology_models.storage.central_unit_user_plane import CentralUnitUserPlane
from vmware.tcsa.collector_sdk.models.topology_models.storage.distributed_unit import DistributedUnit
from vmware.tcsa.collector_sdk.models.topology import TCOTopology
from vmware.tcsa.collector_sdk.models.topology_models.storage.cell_site_group import CellSiteGroup
from vmware.tcsa.collector_sdk.models.topology_models.storage.cell_site import CellSite
from vmware.tcsa.collector_sdk.models.topology_models.sam.container_network_function import ContainerNetworkFunction
import time

VNF_TYPE_MAP = {"CUCP": "CentralUnitControlPlane",
                "CUUP": "CentralUnitUserPlane",
                "DU": "DistributedUnit",
                "FUSION CORE": "Core5gService"
                }


def extract_vnfs(vnf, host, publish_data, start_message):
    timestamp = round(time.time() * 1000)
    # RETRIEVE CNF INSTANCES
    prop_type = VNF_TYPE_MAP.get(vnf.get("vnfProductName", "").upper(), "CNFNotSupported")
    properties = {}
    properties["ClassName"] = prop_type
    properties["type"] = prop_type
    properties["objType"] = "CNFServiceDetail"
    properties["ExternalSource"] = "CNF-SOL-" + host
    properties["Certification"] = "CERTIFIED"
    properties["context"] = host
    properties['Name'] = prop_type + "-" + vnf.get("id")
    properties['Description'] = vnf.get("vnfInstanceDescription")
    properties['IsServiceDysFunctional'] = False
    properties['Name'] = prop_type + "-" + vnf.get("id")
    properties['collector-name'] = start_message.collectorType
    properties['IsEdgeHavingProblem'] = False
    properties['observer'] = "TRUE"
    properties["OpenedAt"] = timestamp
    properties['IsCentralUnitControlPlaneDown'] = False
    properties["CreationClassName"] = prop_type
    properties["DisplayName"] = prop_type + "-" + vnf.get("id")
    properties["IsManaged"] = True
    properties["DisplayClassName"] = prop_type + "-" + vnf.get("id")
    properties["IsVMHostUnResponsive"] = False
    discoveryID = start_message.discoveryID
    timestamp = start_message.timestamp
    name = prop_type + "-" + vnf.get("id")
    type = "CentralUnitControlPlane"
    source = "primary"
    jobID = start_message.jobID
    groupName = start_message.groupName
    action = "r"
    forceRefresh = True
    collectorType = start_message.collectorType
    initialized = True
    ID = start_message.collectorType
    value = 0.0
    metrics = {}
    relations = []
    properties = properties
    if prop_type == "CentralUnitControlPlane":
        type = "CentralUnitControlPlane"
        topology = CentralUnitControlPlane(discoveryID=discoveryID, timestamp=timestamp, name=name, type=type,
                                           Source=source
                                           , jobID=jobID, groupName=groupName, action=action, forceRefresh=forceRefresh,
                                           collectorType=collectorType
                                           , initialized=initialized, ID=ID, value=value, metrics=metrics,
                                           properties=properties, relations=relations)

    elif prop_type == "CentralUnitUserPlane":
        type = "CentralUnitUserPlane"
        topology = CentralUnitUserPlane(discoveryID=discoveryID, timestamp=timestamp, name=name, type=type,
                                        Source=source
                                        , jobID=jobID, groupName=groupName, action=action, forceRefresh=forceRefresh,
                                        collectorType=collectorType
                                        , initialized=initialized, ID=ID, value=value, metrics=metrics,
                                        properties=properties, relations=relations)

    elif prop_type == 'DistributedUnit':
        type = "DistributedUnit"
        topology = DistributedUnit(discoveryID=discoveryID, timestamp=timestamp, name=name, type=type, Source=source
                                   , jobID=jobID, groupName=groupName, action=action, forceRefresh=forceRefresh,
                                   collectorType=collectorType
                                   , initialized=initialized, ID=ID, value=value, metrics=metrics,
                                   properties=properties, relations=relations)


    else:
        type = prop_type
        topology = TCOTopology(discoveryID=discoveryID, timestamp=timestamp, name=name, type=type, Source=source
                               , jobID=jobID, groupName=groupName, action=action, forceRefresh=forceRefresh,
                               collectorType=collectorType
                               , initialized=initialized, ID=ID, value=value, metrics=metrics, properties=properties,
                               relations=relations)
    publish_data.append(topology)
    return topology


def extract_sol_services_or_parents(cnf_data, start_message, publish_data, parent_topology):
    kind = "ContainerNetworkFunction" if cnf_data.get("kind") == 'Service' else cnf_data.get("kind")
    cnf_obj = {}
    parent_id = cnf_data.get("parentId")
    cnf_obj["type"] = kind
    cnf_obj["name"] = kind + "-" + cnf_data.get("objectId")
    cnf_obj["Source"] = start_message.Source
    cnf_obj["forceRefresh"] = True
    cnf_obj["collectorType"] = start_message.collectorType
    cnf_obj["discoveryID"] = start_message.discoveryID
    cnf_obj["jobID"] = start_message.jobID
    cnf_obj["groupName"] = start_message.groupName
    cnf_obj["action"] = "r"
    cnf_obj["initialized"] = True
    cnf_obj["ID"] = start_message.collectorType
    cnf_obj["metrics"] = {}
    cnf_obj["value"] = 0.0
    cnf_obj['relations'] = []
    cnf_obj['properties'] = {
        "Description": "",
        "IsServiceDysFunctional": False,
        "ServiceKey": "",
        "Source": "primary",
        "Name": kind + "-" + cnf_data.get("objectId"),
        "collector-name": start_message.collectorType,
        "IsEdgeHavingProblem": False,
        "observer": "TRUE",
        "OpenedAt": cnf_data.get("_id", {}).get("timestamp", start_message.timestamp),
        "ServiceName": "",
        "CreationClassName": kind,
        "DisplayName": cnf_data.get("name"),
        "IsManaged": True,
        "SystemName": "",
        "DisplayClassName": kind,
        "IsVMHostUnResponsive": True
    }
    if kind == 'ContainerNetworkFunction':
        topology = ContainerNetworkFunction.from_dict(cnf_obj)
        topology.add_OfferedBy(parent_topology)
    else:
        topology = TCOTopology.from_dict(cnf_obj)
        topology.relations = []
        offered_by = {
            "relationName": "OfferedBy",
            "type": parent_topology.type,
            "element": parent_topology.name
        }
        topology.relations.append(offered_by)
    publish_data.append(topology)


def extract_cell_site_details(cell_site, publish_data, start_message):
    cell_site_grp = {}
    if cell_site.get("type").upper() == "CELL_SITE_GROUP":
        obj_type = "CellSiteGroup"
    else:
        obj_type = cell_site.get("type")
    properties = {
        "observer": "TRUE",
        "OpenedAt": cell_site.get("createdTimestamp"),
        "Description": "",
        "ServiceName": "",
        "CreationClassName": obj_type,
        "DisplayName": cell_site.get("name"),
        "IsAnyCellSiteAffected": False,
        "DisplayClassName": "CellSiteGroup",
        "Source": "primary",
        "Name": "CellSiteGroup-" + cell_site.get("name"),
        "collector-name": start_message.collectorType,
    }
    cell_site_grp['type'] = obj_type
    cell_site_grp['Source'] = "primary"
    cell_site_grp["forceRefresh"] = True
    cell_site_grp["collectorType"] = start_message.collectorType
    cell_site_grp["discoveryID"] = start_message.discoveryID
    cell_site_grp["jobID"] = start_message.jobID
    cell_site_grp["groupName"] = start_message.groupName
    cell_site_grp["name"] = "CellSiteGroup-" + cell_site.get("name")
    cell_site_grp["action"] = "r"
    cell_site_grp["initialized"] = True,
    cell_site_grp["ID"] = start_message.collectorType,
    cell_site_grp["metrics"] = {}
    cell_site_grp['properties'] = properties
    cell_site_grp["relations"] = []
    topology = CellSiteGroup.from_dict(cell_site_grp)
    publish_data.append(topology)

    for host_data in cell_site.get("hosts", []):
        extract_cell_site_host_details(host_data, publish_data, topology, start_message)


def extract_cell_site_host_details(host_data, publish_data, parent, start_message):
    cell_site = {}
    timestamp = parent.timestamp
    cell_site["type"] = "CellSite"
    cell_site["Source"] = "primary"
    cell_site["forceRefresh"] = True
    cell_site["collectorType"] = start_message.collectorType
    cell_site["discoveryID"] = start_message.discoveryID
    cell_site["jobID"] = start_message.jobID
    cell_site["groupName"] = "group"
    cell_site["name"] = "CellSite-" + host_data.get("ip")
    cell_site["action"] = "r"
    cell_site["initialized"] = True
    cell_site["ID"] = start_message.collectorType
    cell_site["metrics"] = {}
    cell_site["properties"] = {
        "Description": "",
        "IsCellSiteNotWorking": False,
        "ServiceKey": "",
        "IsHypervisorInfDown": host_data.get("hostSettingStatus"),
        "IsHypervisorResponsive": False,
        "Source": "primary",
        "Name": "CellSite-" + host_data.get("name"),
        "collector-name": start_message.collectorType,
        "observer": "TRUE",
        "OpenedAt": timestamp,
        "IsCellSiteHypervisorAffected": False,
        "ServiceName": "",
        "CreationClassName": "CellSite",
        "DisplayName": host_data.get("name"),
        "IsManaged": True,
        "SystemName": "",
        "IsCellSiteHostNotConfigured": False,
        "parentGroup": parent.properties.get("DisplayName"),
        "DisplayClassName": "CellSite",
        "IsCellSiteNotProvisioned": False
    }
    topology = CellSite.from_dict(cell_site)
    topology.add_ContainedBy(parent)
    publish_data.append(topology)
