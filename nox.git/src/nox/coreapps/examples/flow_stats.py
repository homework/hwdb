from nox.lib.core import *
from nox.lib.openflow import *
import nox.lib.pyopenflow as of
from nox.netapps.monitoring.monitoring import Monitoring
from twisted.python import log
import logging
import MySQLdb as mdb
import sys
import socket, struct
import time

log = logging.getLogger('nox.coreapps.examples.flow_stats')

#transaction ID (xid) initialized here.
xid = -1

#periodic monitoring of the OF switch.
FLOW_MONITOR_INTERVAL = 5 #seconds

class FlowStats(Component):

	def __init__(self, ctxt):
		Component.__init__(self, ctxt)
		self.ctxt = ctxt
		log.debug("Reached the first check-point.")
		self.Monitoring = ctxt.resolve("nox.netapps.monitoring.monitoring.Monitoring")
		log.debug("Reached the second check-point.")
		

	def getInterface(self):
		return str(FlowStats)

	#this method is used for sending flow_stats request.
	#this method is called by the datapath_join_callback method for the very first time, after which it is repeatedly
	#called by the post_callback method.

	def send_flow_stats_request_timer(self, dpid):
		log.debug("I am able to enter the flow_stats_request_timer method.")
		global xid
		flows = of.ofp_match()
		flows.wildcards = of.OFPFW_ALL #wildcarded all match fields, which means that all the flows will be retrieved.
		self.Monitoring.send_flow_stats_request(dpid, flows, 0xff, xid)
		xid += 1
		self.post_callback(FLOW_MONITOR_INTERVAL, lambda : self.send_flow_stats_request_timer(dpid))
		

	#for each new datapath that joins, create a timer loop that monitors the stats of the switches.
	#this method calls the method send_flow_stats_request_timer for the first time.
	def datapath_join_callback(self, dpid, stats):
		self.post_callback(FLOW_MONITOR_INTERVAL, lambda : self.send_flow_stats_request_timer(dpid))

	
	#this method is used for handling the flow stats in
	def flow_stats_in_handler(self, dp_id, flows, more, xid):
		print "----------------Flow Stats report---------------------------"
		#print str(dp_id)+" "+str(flows)
		
		proto = 0
		saddr = 0
		sport = 0
		daddr = 0
		dport = 0
		npkts = 0
		nbytes = 0
		timestamp = 0
	
		for item in flows:
			#print item #this prints individual lists for individual flows


			for key, value in item.iteritems():
				#print [key, value]
				if key == 'packet_count':
					npkts = value
					#print npkts
				if key == 'byte_count':
					nbytes = value
					#print nbytes
				if key == 'match':
					proto = value['nw_proto']
					s_addr = value['nw_src']
					saddr = socket.inet_ntoa(struct.pack('>L', s_addr))
					#print saddr
					sport = value['tp_src']
					d_addr = value['nw_dst']
					daddr = socket.inet_ntoa(struct.pack('>L', d_addr))
					dport = value['tp_dst']
					#print daddr
				#if key == 'actions':
					
				timestamp = int(time.time())
				#print timestamp

			#Database connectivity
			con = mdb.connect('localhost','root','mrl%1%x','homeflow');
			with con:
				cur = con.cursor()
				cur.execute("CREATE TABLE IF NOT EXISTS \
					Flows(proto INT, saddr VARCHAR(16), sport INT, daddr VARCHAR(16), \
					dport INT, npkts INT, nbytes INT, epoch INT(11))")
				cur.execute("INSERT INTO Flows(proto, saddr, sport, daddr, dport, npkts, nbytes, epoch) \
					VALUES ('%d', '%s', '%d', '%s', '%d' , '%d', '%d','%d')" % \
					(proto, saddr, sport, daddr, dport, npkts, nbytes, timestamp))
					
		


	def install(self):
		self.register_for_datapath_join(lambda dpid, stats : self.datapath_join_callback(dpid, stats))
		self.register_for_flow_stats_in(self.flow_stats_in_handler)




def getFactory():
	class Factory:
		def instance(self, ctxt):
			return FlowStats(ctxt)

	return Factory()













