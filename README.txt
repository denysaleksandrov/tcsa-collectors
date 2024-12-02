Create Custom Collectors

Sample custom collector for kafka and rest using python sdk

Prerequisites:
1.	Python3.11 and above
2.	Pip 24.0.0 and above
3.	curl is installed
4.	install zip
5.	Install Python


1.The Collector SDK requires Python users to use Python version 3.11 or higher.
 	Install python and check your version by running:

	python --version
	Note : for Centos and RHEL please install the following dependencies well
	yum install python39
	yum install python39-devel

	Install Pip

	Install pip - Python’s package manager

	Check that you have version 24.0.0 or newer by running:

	pip –version

	If you do not have pip version 24.0.0 or newer, run the following command to install it. This command might require administrative privileges.

	pip install --upgrade pip

	install curl if you don't have curl installed .

2. Download SDK and Extract
	download the package from the developer
	logon to https://developer.vmware.com/sdks
	under Telco Cloud click on VMware TCSA Data Collector Python - SDK
	Select the Appropriate Version and Click on Download
	Once you click On Download Enter your details like Name , Email and Click on Accept EULA.
	the SDK download should start, Allow if any pop up are blocked .


3. Extract the file downloaded in last step

Note : Prerequisite for REDHAT and centos
	yum install python39
	yum install python39-devel

4. Setting up the IDE
	install your favourite IDE e.g. IntelliJ , visual studio code , pycharm.

	import the files (which is downloaded and extracted in last step) in IDE

5. Write the Kafka collector
	install the requirements file using the following command
	pip install -r requirements.txt

	create directory for a collector e.g. kafka_collector .
	inside the collector directory create a python files
	Create or update the required configuration files
	import the base classes from sdk e.g. to create a kafka Collector use like below
	from collectors.stream_collector import StreamCollector

	class KafkaCollector(StreamCollector)
	see sample code for kafka custom collector in example directory

6.  Write the Rest collector
	install the requirements file using the following command
	pip install -r requirements.txt

	create directory for a collector e.g. rest_collector .
	inside the collector directory create a python files
	Create or update the required configuration files
	import the base classes from sdk e.g. to create a rest Collector use like below
	from collectors.batch_collector import BatchCollector

	class HttpCollector(BatchCollector)
	see sample code for rest custom collector in example directory

7.	Build Zip and upload Collector
	Set the env variable TCSA_URL


8.	execute this command to get a list of uploaded collector packages
	curl -k -u admin:changeme $TCSA_URL/dcc/v1/packages

	create or Update the file build_config.json and add/update below info
	"TCSA_IP": "10.225.67.98"
	"TCSA_PORT" : "30002"
	"TCSA_USERNAME" : "admin"
	"TCSA_PASSWORD" : "changeme"
	PROTOCOL": "https"
	"type": "kafka" / "rest"
	Execute below cmd from base directory to build and upload collector package
	./build.sh <collector-directory-name> --upload

Examples:

9.	To build and upload kafka collector, execute below command

	./build.sh <kafka-collector-directory-name> --upload

10.	To build and upload rest collector, execute below command

 	./build.sh <rest-collector-directory-name> --upload

11.	Validate the uploaded collector
	To verify the response contains the collector package

	curl -k -u admin:changeme $TCSA_URL/dcc/v1/packages

12.	Test the collectors
	12.a. Test Kafka Collector

		Please follow the below steps to test the kafka custom collector
		Move examples/kafka_custom_collector directory to base directory collector-sdk
		Modify the configuration as per your requirement
		Later, package can be created and uploaded using build.sh cmd


	12.b. Test Rest Collector

		Please follow the below steps to test the rest custom collector
		Copy examples/rest_custom_collector directory to base directory collector-sdk
		Delete configuration directory from base_directory/rest_custom_collector
		copy files under examples/rest_custom_collector/configuration and put the same in base directory collector-sdk

		Modify the configuration as per your requirement
		Later, package can be created and uploaded using build.sh cmd
		To test the kafka/rest collector, use below cmd

    12.c. Test Topology Rest Collector
        Please follow the below steps to test the topology custom collector
        Copy examples/nfvsol_collector directory to base directory collector-sdk
        Delete configuration directory from base_directory/nfvsol_collector
        copy files under examples/nfvsol_collector/configuration and put the same in base directory collector-sdk
        Modify the configuration as per your requirement
        Later, package can be created and uploaded using build.sh cmd

    12.d. Test Topology Kafka Collector
        Please follow the below steps to test the topology custom collector
        Copy examples/topology_kafka_collector directory to base directory collector-sdk
        Delete configuration directory from base_directory/nfvsol_collector
        copy files under examples/topology_kafka_collector/configuration and put the same in base directory collector-sdk
        Modify the configuration as per your requirement
        Later, package can be created and uploaded using build.sh cmd

	12.e. Test Kafka Avro Custom Collector

		Please follow the below steps to test the kafka avro custom collector
		Copy examples/kafka_avro_custom_collector directory to base directory collector-sdk
		Delete configuration directory from base_directory/kafka_avro_custom_collector
		copy files under examples/kafka_avro_custom_collector/configuration and put the same in base directory collector-sdk

		Modify the configuration as per your requirement
		Later, package can be created and uploaded using build.sh cmd
		To test the kafka/kafka_avro_custom_collector, use below cmd

	 12.f. Test kubernetes Metrics/Events/Topology Collector
        Please follow the below steps to test the kubernetes custom collectors
        Copy examples/k8s_custom_(events/metrics/topology)_collector directory to base directory collector-sdk
        Delete configuration directory from base_directory/k8s_custom_(events/metrics/topology)_collector
        copy files under examples/k8s_custom_(events/metrics/topology)_collector/configuration and put the same in base directory collector-sdk
        Modify the configuration as per your requirement
        Later, package can be created and uploaded using build.sh cmd

	 12.g. Test Netconf Collector
        Please follow the below steps to test the Netconf custom collector
        Copy examples/netconf_collector directory to base directory collector-sdk
        copy files under examples/netconf_collector/configuration and put the same in base directory collector-sdk
        Delete configuration directory from base_directory/netconf_collector
        Modify the configuration as per your requirement
        Later, package can be created and uploaded using build.sh cmd

Test the collector using below cmd,

python3 app.py --directory <directory name where the collector is created> --test --configfile config.json --configschema config_input_schema.json

example
Kafka Custom Collector

python3 app.py --directory kafka_custom_collector --test --configfile config.json --configschema config_input_schema.json

Rest Custom Collector

python3 app.py --directory rest_custom_collector --test --configfile config.json --configschema config_input_schema.json

Kafka Avro Custom Collector

python3 app.py --directory kafka_avro_custom_collector --test --configfile config.json --configschema config_input_schema.json

Test the collector with input file using below cmd,

python3 app.py --directory <directory name where the collector is created> --test --input <input-file> --configfile config.json --configschema config_input_schema.json

example
Kafka Custom Collector

python3 app.py --directory kafka_custom_collector --test --configfile config.json --input input.json --configschema config_input_schema.json

Rest Custom Collector

python3 app.py --directory rest_custom_collector --test --configfile config.json --input input.json --configschema config_input_schema.json

Rest Netconf Collector

python3 app.py --directory netconf_collector --test --configfile config.json --input input.json --configschema config_input_schema.json
13.	Checking Logs for kafka or rest collector
	you can check the output which will be published to kafka further in output.json
	under base directory
	the logs are written in logs/logs.txt
