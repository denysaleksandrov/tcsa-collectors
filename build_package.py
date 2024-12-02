import json
import shutil
import yaml
import sys
import getopt
import os
import requests
import warnings
import urllib.parse
warnings.filterwarnings("ignore")


def upload_package(name, package_name, description):
    print("start upload package")
    build_info = {}
    with open('build_config.json', 'r') as metadata_file:
        build_info = yaml.safe_load(metadata_file)
    tcsa_ip = build_info.get("TCSA_IP", None)
    tcsa_port = build_info.get("TCSA_PORT", None)
    tcsa_protocol = build_info.get("PROTOCOL", "https")
    tcsa_username = build_info.get("TCSA_USERNAME", None)
    tcsa_password = urllib.parse.quote(build_info.get("TCSA_PASSWORD", None), safe='')
    package_type = build_info.get("type", None)
    print(package_type)
    if is_blank(tcsa_ip) or is_blank(tcsa_port) or is_blank(tcsa_username) or is_blank(tcsa_password):
        print("TCSA_IP TCSA_PORT and TCSA_USERNAME and TCSA_PASSWORD are required property"
              " please configure these properties in build_config.json")
        sys.exit(2)
    url = "{protocol}://{ip}:{port}/auth/realms/NGINX/protocol/openid-connect/token". \
        format(protocol=tcsa_protocol, ip=tcsa_ip, port=tcsa_port)
    upload_url = "{protocol}://{ip}:{port}/dcc/v1/packages". \
        format(protocol=tcsa_protocol, ip=tcsa_ip, port=tcsa_port)
    token = get_access_token(url, tcsa_username, tcsa_password)
    payload = {'name': name,
               'description': description,
               'type': package_type}
    files = [
        ('file', (package_name, open(package_name, 'rb'), 'application/zip'))
    ]
    headers = {
        'Authorization': 'Bearer ' + token,

    }

    response = requests.request("POST", upload_url, headers=headers, data=payload, files=files, verify=False)

    if response.status_code == 200:
        print("upload package {package} completed".format(package=package_name))
    else:
        print("error uploading package ", response.text)


def get_access_token(url, tcsa_username, tcsa_password):
    payload = 'grant_type=password&client_id=operation-ui&username={username}&password={password}' \
        .format(username=tcsa_username, password=tcsa_password)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.request("POST", url, headers=headers, data=payload, verify=False)
    return response.json()["access_token"]


def main(argv):
    print("start build collector package")
    arg_input = ""
    arg_help = "{0} -i <input>".format(argv[0])
    upload = False
    try:
        opts, args = getopt.getopt(argv[1:], "hi:u:o:", ["help", "input=",
                                                         "user=", "output=", "upload"])
    except:
        print(arg_help)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(arg_help)  # print the help message
            sys.exit(2)
        elif opt in ("-i", "--input"):
            arg_input = arg
        elif opt in ("--upload"):
            upload = True
    if arg_input.endswith("/"):
        arg_input = arg_input[:-1]
        print(arg_input)
    zipfile_name = arg_input.split("/")[-1]
    description = create_plugin_yaml(arg_input)
    shutil.move("plugin.yaml", arg_input)
    is_exist = os.path.exists("./output/")
    is_exist_dir = os.path.exists("./output/" + arg_input)
    if is_exist_dir:
        shutil.rmtree("./output/")
    if not is_exist:
        os.makedirs("./output/")
    shutil.copytree(arg_input, "./output/" + zipfile_name)
    # shutil.copytree(arg_input, "./output/" + arg_input)
    shutil.copy("config_input_schema.json", "./output/config_input_schema.json")
    shutil.make_archive(zipfile_name, 'zip', "./output/")
    print("build complete")
    if upload:
        upload_package(zipfile_name, zipfile_name + ".zip", description)
        os.remove(zipfile_name + ".zip")
    if os.path.exists("./output/"):
        shutil.rmtree("./output/")


def create_plugin_yaml(collector_dir_name):
    plugin_info = {}
    with open('metadata.json', 'r') as metadata_file:
        plugin_info = yaml.safe_load(metadata_file)
    if os.path.isfile(collector_dir_name + '/plugin.yaml'):
        os.remove(collector_dir_name + '/plugin.yaml')
    name = plugin_info.get('name', None)
    entrypoint = plugin_info.pop("entrypoint", "")
    description = plugin_info['description']
    if is_blank(name) or is_blank(entrypoint) or is_blank(description):
        print("name, entrypoint and description are required property")
        sys.exit(2)
    plugin_info['alias'] = name
    plugin_info['runtime'] = {"main": entrypoint}
    plugin_info['runtime']['tests'] = plugin_info.pop("tests", [])
    plugin_info['requirements'] = []
    plugin_info['repository'] = ''
    with open("plugin.yaml", 'w') as fpo:
        yaml.dump(plugin_info, fpo, indent=2)
    return description


def is_blank(val):
    if val and val.strip():
        return False
    return True


if __name__ == "__main__":
    main(sys.argv)
