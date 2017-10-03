#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""	PING A TODAS LAS IPs DE LAN
* Objeto clase Host contiene IP, Ping y MAC (strings)
* Se escanea con ARPING todas las IPs (devuelve el tiempo y la MAC). Hay que ignorar el localhost porque no hace ping con arping.
* Se devuelve al final listado de IPs encontradas con sus pings y macs

Ejemplos salida comandos arping:
root@Livebox-LEDE:/scripts# arping -c 1 192.168.0.1
ARPING 192.168.0.1 from 192.168.0.42 eth0
Unicast reply from 192.168.0.1 [00:00:00:00:00:00]  1.800ms
Sent 1 probes (1 broadcast(s))
Received 1 response(s)

root@Livebox-LEDE:/scripts# arping -c 1 192.168.0.5
ARPING 192.168.0.5 from 192.168.0.42 eth0
Sent 1 probes (1 broadcast(s))
Received 0 response(s)
"""

import subprocess

rng=254

active_hosts = list()
class Host(object):
	def __init__(self, ip, ping, mac):
		self.ip = ip
		self.ping = ping.replace(" ","").replace("ms","")
		self.mac = mac

for i in range(1,rng+1):
	dest = "192.168.0." + str(i)
	try:
		out = subprocess.check_output(["arping","-c","1",dest]).splitlines()[1]
		
		if "ms" in out: #Host online:
			mac = out.split("[")[1].split("]")[0]
			ping = out.split(" ")[-1]
		
		else: #Host offline:
			raise Exception("Host offline")

	except KeyboardInterrupt:
		break
	except: #Host offline:
		ping = "Offline"
	else: #Host online:
		active_hosts.append( Host(dest, ping, mac) )
	
	print( "IP {} -> {}".format(dest, ping) )

stout = "Hay {} equipos activos:".format( len(active_hosts) )
for i in active_hosts:
	stout += "\n{} ({}ms) [{}]".format(i.ip, i.ping, i.mac)

print(stout)
