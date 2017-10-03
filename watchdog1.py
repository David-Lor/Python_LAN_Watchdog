#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""	PING A TODAS LAS IPs DE LAN
* Objeto clase Host contiene IP y Ping (strings)
* Se escanea con ping y timeout todas las IPs
* Se devuelve al final listado de IPs encontradas con sus pings
"""

import subprocess

rng=254
timeout = 0.8

active_hosts = list()
class Host(object):
	def __init__(self, ip, ping):
		self.ip = ip
		self.ping = ping.replace(" ","").replace("ms","")

for i in range(1,rng+1):
	dest = "192.168.0." + str(i)
	try:
		r = subprocess.check_output(["timeout",str(timeout),"ping",dest,"-t","1","-c","1"]).splitlines()[1].split("time=")[1]
	except KeyboardInterrupt:
		break
	except:
		r = "Offline"
	else:
		active_hosts.append( Host(dest, r) )
	print("IP {} -> {}".format(dest, r))

stout = "Hay {} IPs active_hosts: ".format( len(active_hosts) )
for i in active_hosts:
	stout += "{} ({}ms)".format(i.ip, i.ping)
	if not active_hosts.index(i) == len(active_hosts)-1:
		stout += ", "

print(stout)
