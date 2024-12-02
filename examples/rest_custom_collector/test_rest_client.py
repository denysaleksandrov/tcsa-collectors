"""
# Copyright (c) 2021-2022 VMware, Inc. All rights reserved.
# VMware Confidential
Author: sgondi@vmware.com
"""
import json
from vmware.tcsa.collector_sdk.collect.http import rest_client
from vmware.tcsa.collector_sdk.collect.http.rest_configuration import RestConfiguration
from vmware.tcsa.collector_sdk.collectors.batch_collector import BatchCollector


class TestRestCollector(BatchCollector):

    def __init__(self, logger, config: dict) -> None:
        self._config = config
        super(BatchCollector, self).__init__(logger, config)

    def test_rest_client_apis(self):
        uploadconfiguration = RestConfiguration()
        uploadconfiguration.verify_ssl = False
        uploadconfiguration.host = "https://10.225.67.98:30002"

        payload_upload_token = {'grant_type': 'password', 'client_id': 'operation-ui', 'username': 'admin',
                                'password': 'changeme'}
        headers_upload_token = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        token_res = rest_client.RestClient(configuration=uploadconfiguration).call_api(
            "/auth/realms/NGINX/protocol/openid-connect/token",
            'POST',
            _preload_content=False,
            _return_http_data_only=True,
            post_params=payload_upload_token, header_params=headers_upload_token)

        token_data = json.loads(token_res.read().decode('utf-8'))
        token = token_data['access_token']

        self._logger.info("token [{name}] ".format(name=token))

        payload_upload = {'name': 'http-collector_new', 'description': 'desc_new'}

        files_upload = {'file': 'http-collector.zip'}

        headers_upload = {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'multipart/form-data'

        }
        upload_res_data = rest_client.RestClient(configuration=uploadconfiguration).call_api(
            "/dcc/v1/collectorpackages",
            'POST',
            _preload_content=False,
            _return_http_data_only=True,
            files=files_upload,
            post_params=payload_upload,
            header_params=headers_upload)

        self._logger.info("Collected data [{data}] ".format(data=upload_res_data.data))

        headers_upload_get = {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'

        }

        get_upload_res_data = rest_client.RestClient(configuration=uploadconfiguration).call_api(
            "/dcc/v1/collectorpackages",
            'GET',
            _preload_content=False,
            _return_http_data_only=True,
            header_params=
            headers_upload_get)

        self._logger.info("Collected data [{data}] ".format(data=get_upload_res_data.data))


        smartsconfiguration = RestConfiguration()
        smartsconfiguration.host = "https://10.106.124.64:8443"
        smartsconfiguration.verify_ssl = False
        smartsconfiguration.ssl_ca_cert = "/Users/sgondi/Desktop/TCOPS/collectorSDK/SAMtomcat.cert"
        smartsconfiguration.assert_hostname = "10.106.124.64"

        smarts_res_data = rest_client.RestClient(configuration=smartsconfiguration).call_api(
            "/alerts-edaa/msa/alerts/types/ManagedAlert/instances", 'GET',
            _preload_content=False, _return_http_data_only=True, query_params={"alt": "json"})

        self._logger.info("Collected data [{data}] ".format(data=smarts_res_data.data))


        aciconfiguration = RestConfiguration()
        aciconfiguration.host = "https://sandboxapicdc.cisco.com:443"
        aciconfiguration.verify_ssl = False

        aci_token_res_data = rest_client.RestClient(configuration=aciconfiguration).call_api("/api/aaaLogin.json",
                                                                                             'POST',
                                                                                             body={
                                                                                                 "aaaUser": {
                                                                                                     "attributes": {
                                                                                                         "name": "admin",
                                                                                                         "pwd": "!v3G@!4@Y"}}},
                                                                                             _preload_content=False,
                                                                                             _return_http_data_only=True)

        self._logger.info("headers [{data}] ".format(data=aci_token_res_data.getheaders()))

        aciconfiguration.cookie = aci_token_res_data.getheader(name="Set-Cookie")

        aci_res_node_data = rest_client.RestClient(configuration=aciconfiguration).call_api(
            "/api/class/fabricNode.json", 'GET',
            _preload_content=False,
            _return_http_data_only=True)

        self._logger.info("Collected Data [{data}] ".format(data=aci_token_res_data.data))

        vcdconfiguration = RestConfiguration()
        vcdconfiguration.host = "https://10.62.72.33:443"
        vcdconfiguration.verify_ssl = False
        vcdconfiguration.username = "administrator@system"
        vcdconfiguration.password = "Dangerous!11"
        token = vcdconfiguration.get_basic_auth_token()
        vcd_res_data = rest_client.RestClient(configuration=vcdconfiguration) \
            .call_api("/api/sessions", 'POST', _preload_content=False,
                      _return_http_data_only=True,
                      header_params={'Accept': 'application/*+xml;version=34.0', 'Authorization': token})

        vcd_header_data = vcd_res_data.getheader(name="x-vcloud-authorization")

        vcd_get_res_data = rest_client.RestClient(configuration=vcdconfiguration) \
            .call_api("/api/org", 'GET', _preload_content=False,
                      _return_http_data_only=True,
                      header_params={'Accept': 'application/*+xml;version=35.0',
                                     'x-vcloud-authorization': vcd_header_data})

        self._logger.info("Collected Data [{data}] ".format(data=vcd_get_res_data.data))

