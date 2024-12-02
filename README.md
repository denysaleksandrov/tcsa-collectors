# Create Custom Collectors

Sample custom collector for kafka and rest using python sdk

####Prerequisites:
<li> Python3.11 and above 
<li>Pip 24.0.0 and above
<li> curl is installed
<li> install zip

### Install Python

####1.The Collector SDK requires Python users to use Python version 3.11 or higher. 
Install python and check your version by running:

    python --version

#####for Centos and RHEL please install the following dependencies well 
<code>
yum install python39<br>
yum install python39-devel</code>

### Install Pip

Install pip - Python’s package manager
 
Check that you have version 24.0.0  or newer by running:

    pip --version

If you do not have pip version 24.0.0  or newer, run the following command to install it. This command might require administrative privileges.

    pip install --upgrade pip

### Install curl

install curl if you don't have curl installed .

### Download SDK and Extract
<ol>
   <li>download the package from the developer portal 
   <li>logon to https://developer.vmware.com/sdks
   <li>under Telco Cloud click on VMware TCSA Data Collector Python - SDK
   <li>Select the Appropriate Version and Click on Download
   <li>Once you click On Download Enter your details like Name , Email and Click on Accept EULA.the SDK download should start, Allow if any pop up are blocked .
</ol>
Extract the file downloaded in last step

### Prerequisite for REDHAT and centos
install python3 devel yum install python36-devel

### Setting up the IDE

install your favourite IDE e.g. IntelliJ , visual studio code , pycharm.

import the files (which is downloaded and extracted in last step) in IDE


### Write the Kafka collector 

<ol>
  <li> install the requirements file using the following command</li>

    pip install -r requirements.txt

  <li>create directory for a collector e.g. kafka_collector . </li>
  <li>inside the collector directory create a python files </li>
  <li>Create or update the required configuration files</li>
  <li> import the base classes from sdk e.g. to create a kafka Collector use like below

    from collectors.stream_collector import StreamCollector

    class KafkaCollector(StreamCollector)
</li>
  <li>see sample code for kafka custom collector in example directory</li>
</ol>

#### Write the Rest collector

<ol>
  <li> install the requirements file using the following command</li>

    pip install -r requirements.txt

  <li>create directory for a collector e.g. rest_collector . </li>
  <li>inside the collector directory create a python files </li>
  <li>Create or update the required configuration files</li>
  <li> import the base classes from sdk e.g. to create a rest Collector use like below

    from collectors.batch_collector import BatchCollector
    
    class HttpCollector(BatchCollector)
</li>
  <li>see sample code for rest custom collector in example directory</li>
</ol>

#### Build Zip and upload Collector
<ol>
<li>Set the env variable TCSA_URL
<li>execute this command to get a list of uploaded collector packages

    curl -k -u admin:changeme $TCSA_URL/dcc/v1/packages

<li>create or Update the file build_config.json and add/update below info
   
    "TCSA_IP": "10.225.67.98"
    "TCSA_PORT" : "30002"
    "TCSA_USERNAME" : "admin"
    "TCSA_PASSWORD" : "changeme"
    PROTOCOL": "https"
    "type": "kafka" / "rest"

<li> Execute below cmd from base directory to build and upload collector package</li>

    ./build.sh <collector-directory-name> --upload

<li>Examples:

To build and upload kafka collector, execute below command

    ./build.sh <kafka-collector-directory-name> --upload

To build and upload rest collector, execute below command

    sh build.sh <rest-collector-directory-name> --upload

</ol>

### Validate the uploaded collector

To verify the response contains the collector package

    curl -k -u admin:changeme $TCSA_URL/dcc/v1/packages

## Test the collectors

### Test Kafka Collector

<ol>
Please follow the below steps to test the kafka custom collector
<li>Move examples/kafka_custom_collector directory to base directory collector-sdk
<li>Modify the configuration as per your requirement
<li>Later, package can be created and uploaded using build.sh cmd</li>
</ol>

### Test Rest Collector
<ol>
Please follow the below steps to test the rest custom collector
<li>Copy examples/rest_custom_collector directory to base directory collector-sdk
<li>Delete configuration directory from base_directory/rest_custom_collector
<li>copy files under examples/rest_custom_collector/configuration and put the same in base directory collector-sdk
<li>Modify the configuration as per your requirement
<li>Later, package can be created and uploaded using build.sh cmd
</ol>

### Test Kafka Avro Collector
<ol>
Please follow the below steps to test the Kafka Avro Custom Custom collector
<li>Copy examples/kafka_avro_custom_collector directory to base directory collector-sdk
<li>Delete configuration directory from base_directory/kafka_avro_custom_collector
<li>copy files under examples/kafka_avro_custom_collector/configuration and put the same in base directory collector-sdk
<li>Modify the configuration as per your requirement
<li>Later, package can be created and uploaded using build.sh cmd
</ol>

### Test Topology Rest Collector
<ol>
Please follow the below steps to test the topology custom collector
<li>Copy examples/nfvsol_collector directory to base directory collector-sdk
<li>Delete configuration directory from base_directory/nfvsol_collector
<li>copy files under examples/nfvsol_collector/configuration and put the same in base directory collector-sdk
<li>Modify the configuration as per your requirement
<li>Later, package can be created and uploaded using build.sh cmd
</ol>

### Test Topology Kafka Collector
<ol>
Please follow the below steps to test the topology custom collector
<li>Copy examples/topology_kafka_collector directory to base directory collector-sdk
<li>Delete configuration directory from base_directory/nfvsol_collector
<li>copy files under examples/topology_kafka_collector/configuration and put the same in base directory collector-sdk
<li>Modify the configuration as per your requirement
<li>Later, package can be created and uploaded using build.sh cmd
</ol>

### Test Kubernetes Metrics/Events/Topology Collector
<ol>
Please follow the below steps to test the kubernetes custom collectors
<li>Copy examples/k8s_custom_(events/metrics/topology)_collector directory to base directory collector-sdk
<li>Delete configuration directory from base_directory/k8s_custom_(events/metrics/topology)_collector
<li>copy files under examples/k8s_custom_(events/metrics/topology)_collector/configuration and put the same in base directory collector-sdk
<li>Modify the configuration as per your requirement
<li>Later, package can be created and uploaded using build.sh cmd
</ol>
### Test Netconf Collector
<ol>
Please follow the below steps to test the kubernetes custom collectors
<li>Copy examples/netconf_collector directory to base directory collector-sdk
<li>copy files under examples/netconf_collector/configuration and put the same in base directory collector-sdk
<li>Delete configuration directory from base_directory/netconf_collector
<li>Modify the configuration as per your requirement
<li>Later, package can be created and uploaded using build.sh cmd
</ol>

### To test the custom collector, use below cmd

    python3 app.py --directory <directory name where the collector is created> --test --configfile config.json --configschema config_input_schema.json 

example
<br>
Kafka Custom Collector<br>
python3 app.py --directory kafka_custom_collector --test --configfile config.json --configschema config_input_schema.json
<br>
Rest Custom Collector<br>
<code>
python3 app.py --directory rest_custom_collector --test --configfile config.json --configschema config_input_schema.json
</code>
<br>
Kafka Avro Custom Custom Collector<br>
<code>
python3 app.py --directory kafka_avro_custom_collector --test --configfile config.json --configschema config_input_schema.json
</code>
Netconf Collector<br>
<code>
python3 app.py --directory netconf_collector --test --configfile config.json --configschema config_input_schema.json
</code>

### To test the custom collector with input file, use below cmd

    python3 app.py --directory <directory name where the collector is created> --test --input <input-file> --configfile config.json --configschema config_input_schema.json 

example
<br>
Kafka Custom Collector<br>
<code>
python3 app.py --directory kafka_custom_collector --test --input input.json --configfile config.json --configschema config_input_schema.json
</code>
<br>
Rest Custom Collector<br>
<code>
python3 app.py --directory rest_custom_collector --test --input input.json --configfile config.json --configschema config_input_schema.json
</code>

### Checking Logs for kafka or rest collector
you can check the output which will be published to kafka further in output.json under base directory
<br>
the logs are written in logs/logs.txt