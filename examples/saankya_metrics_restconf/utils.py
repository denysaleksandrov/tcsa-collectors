"""
# Copyright (c) 2021-2023 VMware, Inc. All rights reserved.
# VMware Confidential
"""
import json
import xmltodict
import datetime
import gunicorn.app.base


def xml2jsonConvertor(xml_data):
    data_dict = xmltodict.parse(xml_data)
    # Convert the dictionary to JSON
    collected_data = json.dumps(data_dict, indent=2)
    return json.loads(collected_data)


def datetime_to_epoch(datetime_str, format_str):
    if datetime_str is None or datetime_str == "":
        return ""

    # convert ISO-formatted string to datetime object
    datetime_obj = datetime.datetime.strptime(datetime_str, format_str)

    # convert datetime object to epoch time
    return int(datetime_obj.timestamp())


class GunicornApplication(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application
