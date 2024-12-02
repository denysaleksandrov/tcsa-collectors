import json
import lazy_write
from pathlib import Path
import os.path
import argparse
import json
import requests
import sys
from genson import SchemaBuilder
from pathlib import Path
from typing import Any, Dict, List, Optional
from caseconverter import snakecase
import os.path

import lazy_write

default_properties = ["domain", "sub_domains", "metricType"]
default_values = {"processedTimestamp": "int(time.time()*1000)"}
default_data_types = {
    "processedTimestamp" : "int",
    "timestamp": "int",
    "metrics": "dict",
    "properties": "dict",
    "tags": "dict"
}


def spaces(level: int):
    return ' ' * Config.indent * level


def indent_class(code: str, level: int):
    return Config.line_break.join(indent_line(line, level) for line in code.splitlines())


def indent_line(line: str, level: int):
    return spaces(level=level) + line if line else ''


class Config:
    indent: int = 4
    line_break: str = '\n'
    generate_repr_method: bool = False
    generate_validate_code: bool = False
    override_generated_class: bool = False


def extract_keys(json_data):
    primitive_properties = {}
    dict_properties = {}
    # to_class_code(0)
    for key in json_data:
        # print(key)
        if key in ["domain", "sub_domains", "metricType"]:
            primitive_properties[key] = json_data.get(key)
        elif key in ["metrics", "properties", "tags"]:
            dict_properties[key] = {}
        elif key in ['tco_internal']:
            for val in json_data.get(key):
                if val == 'colltimestamp':
                    primitive_properties['timestamp'] = ''
                else:
                    primitive_properties[val] = ''
    return [primitive_properties, dict_properties]


def generate_default_constructor():
    result = [f'{spaces(1)}def __init__(self):', f'{spaces(2)}pass']
    result.append(f'{spaces(1)}')
    return result

def generate_default_metrics_method(dict_properties, json_schema):
    result = []
    for property in dict_properties:
        is_property_added = []
        result.append(f'{spaces(1)}@staticmethod')
        result.append(f'{spaces(1)}def default_{property}():')
        open_brace = '{'
        close_brace = '}'
        result.append(f'{spaces(2)}return {open_brace}')
        for metric in json_schema.get(property, []):
            key = metric.get("name")
            if key not in is_property_added:
                result.append(f'{spaces(2)} "{key}": None,')
                is_property_added.append(key)
        result.append(f'{spaces(2)}{close_brace}')
        result.append(f'{spaces(1)}')
    result.append(f'{spaces(1)}')
    return result


def to_class_code(class_name, parent_class, primitive_properties, dict_properties, json_schema) -> str:
    result = []
    result = result + add_imports()
    result.append(f'class {class_name}({parent_class}):')
    result.append(f'{spaces(1)}')
    prop_str = ''
    default_prop_str = ''
    for prop in primitive_properties:
        data_type = default_data_types.get(prop, "str")
        result.append(f'{spaces(1)}{prop}: {data_type}')
        prop_str = prop_str + prop + ", "
        default_prop_str = default_prop_str + prop + '=None, '
    for prop in dict_properties:
        data_type = default_data_types.get(prop, "str")
        result.append(f'{spaces(1)}{prop}: {data_type}')
        prop_str = prop_str + prop + ", "
        default_prop_str = default_prop_str + prop + '=None, '
    default_prop_str = default_prop_str[:-2]

    prop_str = prop_str[:-2]
    result.append(f'{spaces(1)}')
    # TODO add default constructor
    result = result + generate_default_constructor()
    # TODO add from_dict class method
    result = result + generate_from_dict_method(primitive_properties, dict_properties, prop_str, json_schema,
                                                class_name)
    # TODO add all args constructor
    result = result + generate_all_args_constructor(primitive_properties, dict_properties, default_prop_str, json_schema,
                                                    class_name)
    # TODO add toJson Method
    result = result + generate_to_json_method()
    # TODO add default Metrics
    result = result + generate_default_metrics_method(dict_properties, json_schema)

    code = Config.line_break.join(result)
    return indent_class(code=code, level=0)


def generate_from_dict_method(primitive_properties, dict_properties, prop_str, json_schema, class_name):
    result = [f'{spaces(1)}@classmethod', f'{spaces(1)}def from_dict(cls, d):']
    default_dict = {}
    for prop in primitive_properties:
        if prop in default_properties:
            val = json_schema.get(prop)
            if type(val) == str:
                result.append(f'{spaces(2)}{prop} = "{val}"')
            else:
                result.append(f'{spaces(2)}{prop} = {val}')
        elif prop in default_values:
            val = default_values.get(prop)
            result.append(f'{spaces(2)}{prop} = d.get("{prop}", {val})')
        else:
            result.append(f'{spaces(2)}{prop} = d.get("{prop}", None)')
    for prop in dict_properties:
        result.append(f'{spaces(2)}{prop} = {class_name}.default_{prop}()')
        result.append(f'{spaces(2)}{prop}_temp = d.get("{prop}", {default_dict})')
        result.append(f'{spaces(2)}{prop}.update({prop}_temp)')

    cons_str = '(' + prop_str + ')'
    result.append(f'{spaces(2)}return cls{cons_str}')
    result.append(f'{spaces(1)}')
    return result


def generate_all_args_constructor(primitive_properties, dict_properties, default_prop_str, json_schema,
                                  class_name):
    result = [f'{spaces(1)}def __init__(self, {default_prop_str}):']
    for prop in primitive_properties:
        if prop in default_properties:
            val = json_schema.get(prop)
            if type(val) == str:
                result.append(f'{spaces(2)}self.{prop} = "{val}"')
            else:
                result.append(f'{spaces(2)}self.{prop} = {val}')
        elif prop in default_values:
            val = default_values.get(prop)
            result.append(f'{spaces(2)}self.{prop} = {prop} if {prop} is  not None else {val}')
        else:
            result.append(f'{spaces(2)}self.{prop} = {prop}')
    for prop in dict_properties:
        result.append(f'{spaces(2)}{prop}_defaults = {class_name}.default_{prop}()')
        result.append(f'{spaces(2)}{prop}_defaults.update({prop})')
        result.append(f'{spaces(2)}self.{prop} = {prop}_defaults')
    result.append(f'{spaces(1)}')
    return result


def generate_to_json_method():
    result = [f'{spaces(1)}def toJSON(self):']
    result.append(f'{spaces(2)}return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)')
    result.append(f'{spaces(1)}')
    return result


def add_imports():
    result = []
    result.append(f'{spaces(0)}import json')
    result.append(f'{spaces(0)}import time')
    result.append(f'{spaces(0)}from vmware.tcsa.collector_sdk.models.metric import TCOMetric')
    result.append(f'{spaces(0)}')
    result.append(f'{spaces(0)}')
    return result


def generate_python_file(code, output_path: Path):
    lazy_write.write(output_path, code)


def get_access_token(url, tcsa_username, tcsa_password):

    payload = 'grant_type=password&client_id=operation-ui&username={username}&password={password}' \
        .format(username=tcsa_username, password=tcsa_password)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.request("POST", url, headers=headers, data=payload, verify=False)
    return response.json()["access_token"]


def generatePythonClasses(tcsa_ip, tcsa_port, tcsa_username, tcsa_password, tcsa_protocol):

    if is_blank(tcsa_ip) or is_blank(tcsa_port) or is_blank(tcsa_username) or is_blank(tcsa_password):
        print("TCSA_IP and TCSA_PORT are required property"
              " please provide as an arg")
        sys.exit(2)
    url = "{protocol}://{ip}:{port}/auth/realms/NGINX/protocol/openid-connect/token". \
        format(protocol= tcsa_protocol, ip=tcsa_ip, port=tcsa_port)
    catalog_url = "{protocol}://{ip}:{port}/v2/catalog/metric-entities". \
        format(protocol= tcsa_protocol, ip=tcsa_ip, port=tcsa_port)
    token = get_access_token(url, tcsa_username, tcsa_password)
    headers = {
        'Authorization': 'Bearer '+ token,
    }
    response = requests.request("GET", catalog_url, headers=headers, verify=False)

    return response.json()


def is_blank(val):
    if val and val.strip():
        return False
    return True


def main():  # pragma: no cover
    print("Start generating classes for metric Models ")
    arg_parser = argparse.ArgumentParser(description='JSON Schema to Python Class')
    #arg_parser.add_argument('schema_path', type=str)
    arg_parser.add_argument('-host', '--host', type=str, default=None)
    arg_parser.add_argument('-port', '--port', type=str, default=None)
    arg_parser.add_argument('-user', '--user', type=str, default="admin")
    arg_parser.add_argument('-pwd', '--pwd', type=str, default="changeme")
    arg_parser.add_argument('-protocol', '--protocol', type=str, default="https")
    arg_parser.add_argument('-o', '--output-path', type=str, default=None)
    arg_parser.add_argument('-i', '--indent', type=int, default=4)
    arg_parser.add_argument('--repr', action='store_true', help='generate __repr__ method', default=True)
    arg_parser.add_argument('--validate', action='store_true', help='validate schema', default=False)
    arg_parser.add_argument('--override', action='store_false', help='override generated class', default=True)

    arguments = arg_parser.parse_args()
    Config.indent = arguments.indent
    Config.generate_repr_method = arguments.repr
    Config.generate_validate_code = arguments.validate
    Config.override_generated_class = arguments.override

    json_data = generatePythonClasses(arguments.host, arguments.port, arguments.user, arguments.pwd, arguments.protocol)
    entities = json_data["entity"]
    for entity in entities:
        metricType = entity["metricType"]
        file_name = snakecase(metricType)
        if file_name is not None and file_name[0].isdigit():
            file_name = "_" + file_name
        json_struct = entity
        primitive_properties, dict_properties = extract_keys(json_struct)
        code = to_class_code(file_name, "TCOMetric", primitive_properties, dict_properties, json_struct)

        #If Domain (Package name) starts with a digit, append underscore at the prefix.
        domain = snakecase(entity["domain"])
        if domain is not None and domain[0].isdigit():
            domain = "_" + domain

        dir_path = "models/" + domain + "/"
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        Path(dir_path+"__init__.py").touch(exist_ok=True)
        if arguments.host is None or arguments.port is None:
            print("Host and Port cannot be empty")
        else:
            file_path = dir_path + file_name +".py"
            if not os.path.exists(file_path) or Config.override_generated_class:
                print("Generating python class  - " + file_path)
                generate_python_file(code, Path(file_path))

if __name__ == '__main__':
    main()

