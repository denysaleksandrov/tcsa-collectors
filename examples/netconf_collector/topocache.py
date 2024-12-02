from threading import Thread
import time

class TopoCache(Thread):
	def __init__(self, session, logger, config):
		Thread.__init__(self)
		self._session=session
		self._logger=logger
		self._config=config
		self._mapping = {} 
		self._ready = False
		self._elementName=None
		self._smartsMapping = {"PSU" : "PowerSupply", "RFD" : "Card", "CAT" : "...", "SUI" : "..."}
		self._SoNumMap = {}


	def setSession(self,session):
		self._session=session #In case of reconnect exposing an option to set the session from outside.

	def getType(self, inst):
		return self._mapping[inst] if inst in self._mapping else "GenericComponentType"

	def getInstName(self, inst):
		return inst + "(" + self._SoNumMap[inst] + ")" if inst in self._SoNumMap else inst

	def getElementName(self):
		return self._elementName if  self._elementName else "CompscopeNE"

	def isReady(self):
		return self._ready

	def run(self):
		ns="{urn:ietf:params:xml:ns:netconf:base:1.0}"
		while(True):
			try:
				self._logger.debug("Start loading the cache");
				mapping={}
				soNoMapping={}
				filterExp="<network-element-pac></network-element-pac>"
				data=self._session.get(filter=("subtree", filterExp)).data_ele
				for elem in data.getchildren():
					for innerelem in elem.getchildren():
						if innerelem.tag == "network-element":
							self._elementName=innerelem.text
							break
				self._logger.debug("Equipment name %s ", self._elementName)
				filterExp="<equipment></equipment>"
				data=self._session.get(filter=("subtree",filterExp)).data_ele

				#Weird the namespace for first block is different from all the others
				for elem in data.getchildren():
					instNameTag=elem.find(".//uuid")
					if instNameTag is not None:
						instName= instNameTag.text
						instType=elem.find(".//equipment-type/type-name").text
						serialNo = elem.find(".//equipment-instance/serial-number").text
					else:
						instName=elem.find(".//" + ns+ "uuid").text
						instType=elem.find(".//" + ns + "equipment-type/" + ns + "type-name").text
						serialNo=elem.find(".//" + ns + "equipment-instance/" + ns + "serial-number").text
					self._logger.debug("Type Mapping %s:%s:%s", instName, instType, serialNo)
					soNoMapping[instName]=serialNo
					mapping[instName]=instType
				self._mapping=mapping #TODO: should it be inside lock.
				self._SoNumMap = soNoMapping;
				self._logger.debug("Completed loading the cache");
				#Load the cache...
				self._ready=True
				time.sleep(100); #TODO take the refresh timeout from conf
			except Exception as e:
				#TODO: Refine it For session timeout related exceptions
				self._logger.error("Exception %s", e)
				time.sleep(10); # Sleep for a time greater than or equal to the reconnect time.
