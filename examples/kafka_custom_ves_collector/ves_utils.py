import json
from jsonpath_ng.ext import parse
from jsonschema import validate


def read_json_file(filename):
    with open(filename) as json_data:
        data = json.load(json_data)
        return data


def parse_json_path(expresssion,input_json):
    # print(expresssion)
    jsonpath_expression = parse(str(expresssion))
    output = jsonpath_expression.find(input_json)
    return output

def parse_json_path_with_index(expresssion,input_json,index):
    if "[*]" in expresssion:
        expresssion=expresssion.replace("[*]","[{index}]".format(index=index))
    jsonpath_expression = parse(str(expresssion))
    output = jsonpath_expression.find(input_json)
    return output




def evalute_dict_mapper(mapper,input,index):
    output={}
    for key, value in mapper.items():
        if str(key).startswith("$."):
            key=parse_json_path_with_index(key,input,index)[0].value
        if str(value).startswith("$."):
            value=parse_json_path_with_index(value,input,index)[0].value
        output[key]=value
    return output




def convert_to_tco_metrics(mapper,input,type,ves_schema):
    # validate collector_data with ves_json_schema
    if ves_schema:
        validate(input,ves_schema)
    tco_matric = {}
    metrics_dict = {}
    properties_dict = {}
    tags_dict = {"dcName": "_core"}
    for key, value in mapper.items():
        if str(key)=='tags' and value is not None and value != "":
            tags_value=parse_json_path(str(value),input)[0].value
            tags_dict.update(tags_value)
            continue
        if str(key).startswith("tags."):
            tags_key = str(key).split("tags.")[1]
            # print(tags_key)
            if str(value).startswith("$."):
                tags_value = parse_json_path(str(value), input)
                tags_dict[tags_key] = tags_value[0].value
            else:
                tags_dict[tags_key] = value
            continue
        if str(key).startswith("properties."):
            properties_key = str(key).split("properties.")[1]
            # print(properties_key)
            if str(value).startswith("$."):
                properties_value = parse_json_path(str(value), input)
                properties_dict[properties_key] = properties_value[0].value
            else:
                properties_dict[properties_key] = value
            continue
        if str(key).startswith("metrics.$"):
            # print(key)
            key_expression = str(key).split("metrics.", 1)[1]
            metrics_type = "default"
            if "Array" in key_expression:
                metrics_type = str(key_expression.split("Array")[0]).split("'")[-1]
                # print(metrics_type)
                metrics_dict[metrics_type] = {}
                output = parse_json_path(str(key_expression), input)
                value_json_expression = None
                # if "[*]" in str(value):
                #     value_json_expression = str(value).replace("[*]", "[{i}]")
                if len(output) >= 1:
                    for i in range(0, len(output)):
                        metrics_key = output[i].value
                        if isinstance(value, dict):
                            metrics_dict[metrics_type][metrics_key] =evalute_dict_mapper(value,input,i)
                            continue
                        if "[*]" in str(value):
                            value_json_expression = str(value).replace("[*]", "[{i}]")
                        temp = str(value_json_expression).format(i=i)
                        value_output = parse_json_path(temp, input)
                        metrics_value = value_output[0].value
                        # print(metrics_value)
                        metrics_dict[metrics_type][metrics_key] = metrics_value

            else:
                metric_key=parse_json_path(key_expression,input)[0].value
                metric_value=parse_json_path(str(value),input)[0].value if str(value).startswith("$.") else value
                metrics_dict[metric_key]=metric_value
            continue
        if str(value).startswith("$."):
            output = parse_json_path(str(value), input)
            if len(output) == 1:
                tco_matric[key] = output[0].value
        if not str(value).startswith("$."):
            tco_matric[key] = value
    # print(json.dumps(metrics_dict))
    # tco_matric.pop("metrics.*")
    # print(json.dumps(properties_dict))
    if type == "metrics":
        tco_matric["properties"] = properties_dict
        tco_matric["metrics"] = metrics_dict
    tco_matric['tags'] = tags_dict
    # print(json.dumps(tco_matric))
    return tco_matric
