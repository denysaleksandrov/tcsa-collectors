import argparse
import os
from vmware.tcsa.collector_sdk.engine import PluginEngine
import yaml
import sys

APP_PLUGIN_DIR = '/app/plugins/'


def __description() -> str:
    return "Create your own collector using python SDK"


def __usage() -> str:
    return "vrv-meta.py --service vrv"


def __init_cli() -> argparse:
    parser = argparse.ArgumentParser(description=__description(), usage=__usage())
    parser.add_argument(
        '-l', '--log', default='DEBUG', help="""
        Specify log level which should use. Default will always be DEBUG, choose between the following options
        CRITICAL, ERROR, WARNING, INFO, DEBUG
        """
    )
    parser.add_argument(
        '-d', '--directory', default=f'{APP_PLUGIN_DIR}', help="""
        (Optional) Supply a directory where plugins should be loaded from. The default is ./plugins
        """
    )
    parser.add_argument(
        '-c', '--configfile', default=f'{"config.json"}', help="""
        (Optional) Supply a directory where plugins should be loaded from. The default is config.json
        """
    )
    parser.add_argument(
        '-t', '--test', action='store_true', help=""", 
        (Optional) Supply a argument if need to execute collector in test. The default is false.
        """
    )
    parser.add_argument(
        '-i', '--input', default=f'{""}', help=""", 
        (Optional) Supply a argument if need to input the data from file. The default is input.json
        """
    )
    parser.add_argument(
        '-o', '--outputfile', default=f'output.json', help="""
        (Optional) Supply a argument if need to write output in file for test . The default is output.txt.
        """
    )
    parser.add_argument(
        '-lf', '--logfile', default=f'logs.txt', help="""
        (Optional) Supply a argument if need to write output in file for test and test is enabled. The default is logs.txt.
        """
    )
    parser.add_argument(
        '-cs', '--configschema', default=f'{"config_input_schema.json"}', help="""
        (Optional) Supply a directory where plugins should be loaded from. The default is ./plugins
        """
    )

    return parser;


def __print_program_end() -> None:
    print("-----------------------------------")
    print("End of execution")
    print("-----------------------------------")


def __init_app(parameters: dict) -> None:
    PluginEngine(options=parameters).start()


def __generate_test_configs(is_test: bool, directory: str):
    if is_test:
        current_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(current_path,'metadata.json'), 'r') as metadata_file:
            plugin_info = yaml.safe_load(metadata_file)
        if os.path.isfile(os.path.join(current_path,directory,'plugin.yaml')):
            os.remove(os.path.join(current_path,directory,'plugin.yaml'))
        name = plugin_info.get('name', None)
        entrypoint = plugin_info.pop("entrypoint", "")
        description = plugin_info['description']
        plugin_info['alias'] = name
        plugin_info['runtime'] = {"main": entrypoint}
        plugin_info['runtime']['tests'] = plugin_info.pop("tests", [])
        plugin_info['requirements'] = []
        plugin_info['repository'] = ''
        if is_blank(name) or is_blank(entrypoint) or is_blank(description):
            print("name, entrypoint and description are required property")
            sys.exit(2)
        with open((os.path.join(current_path,directory,'plugin.yaml')), 'w') as fpo:
            yaml.dump(plugin_info, fpo, indent=2)

def is_blank(val):
    return False if val and val.strip() else True

if __name__ == '__main__':
    # import sys
    #
    # for i in range(1, len(sys.argv)):
    #     print('argument:', i, 'value:', sys.argv[i])
    __cli_args = __init_cli().parse_args()
    __generate_test_configs(__cli_args.test, __cli_args.directory)
    __init_app({
        'log_level': __cli_args.log,
        'directory': __cli_args.directory,
        'config': __cli_args.configfile,
        'test': __cli_args.test,
        'input': __cli_args.input,
        'logfile': __cli_args.logfile,
        'output_file': __cli_args.outputfile,
        'config_schema': __cli_args.configschema,
        "current_path": os.path.dirname(os.path.realpath(__file__))
    })
