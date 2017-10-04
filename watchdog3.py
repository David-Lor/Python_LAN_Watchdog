#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""	PING A TODAS LAS IPs DE LAN
* Objeto clase Host contiene IP, Ping y MAC (strings)
* Se escanea con ARPING todas las IPs (devuelve el tiempo y la MAC). Hay que ignorar el localhost porque no hace ping con arping.
* Se devuelve al final listado de IPs encontradas con sus pings y macs
* Se determina si un host (ip y mac) es Conocido (estaba definido en archivo config DHCP [static dhcp leases]) o si es Desconocido

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

Ejemplo salida lectura archivo /etc/config/dhcp:
>>> f=open("/etc/config/dhcp","r")
>>> o=f.read()
>>> oo=o.splitlines()
>>> oo
['', 'config dnsmasq', "\toption domainneeded '1'", "\toption localise_queries '1'", "\toption rebind_protection '1'", "\toption rebind_localhost '1'", "\toption local '/lan/'", "\toption domain 'lan'", "\toption expandhosts '1'", "\toption authoritative '1'", "\toption readethers '1'", "\toption leasefile '/tmp/dhcp.leases'", "\toption resolvfile '/tmp/resolv.conf.auto'", "\toption localservice '1'", "\toption sequential_ip '1'", "\toption nonwildcard '0'", "\tlist server '213.60.205.175'", "\tlist server '8.8.8.8'", "\tlist server '213.60.205.174'", "\tlist server '8.8.4.4'", "\tlist server '213.60.205.173'", "\tlist server '208.67.222.222'", "\tlist server '208.67.220.220'", '', "config dhcp 'lan'", "\toption interface 'lan'", "\toption start '210'", "\toption limit '239'", "\toption netmask '255.255.255.0'", "\tlist dhcp_option '3,192.168.0.1'", "\tlist dhcp_option '6,213.60.205.175,213.60.205.173,213.60.205.174,8.8.8.8,8.8.4.4'", "\toption leasetime '1h'", '', "config dhcp 'wan'", "\toption interface 'wan'", "\toption ignore '1'", '', "config odhcpd 'odhcpd'", "\toption maindhcp '0'", "\toption leasefile '/tmp/hosts/odhcpd'", "\toption leasetrigger '/usr/sbin/odhcpd-update'", '', 'config host', "\toption name 'Asus_D541S_LAN'", "\toption ip '192.168.0.32'", "\toption mac '00:00:00:00:00:00'", '', 'config host', "\toption name 'Asus_D541S_WIFI'", "\toption ip '192.168.0.31'", "\toption mac '00:00:00:00:00:00'", '', 'config host', "\toption name 'XperiaL'", "\toption mac '00:00:00:00:00:00'", "\toption ip '192.168.0.83'", '', 'config host', "\toption name 'Core2Duo'", "\toption mac '00:00:00:00:00:00'", "\toption ip '192.168.0.13'", '', 'config host', "\toption name 'GalaxyS4'", "\toption mac '00:00:00:00:00:00'", "\toption ip '192.168.0.81'", '', 'config host', "\toption name 'Huawei'", "\toption mac '00:00:00:00:00:00'", "\toption ip '192.168.0.88'", '', 'config host', "\toption name 'RPi1'", "\toption mac '00:00:00:00:00:00'", "\toption ip '192.168.0.101'", '', 'config host', "\toption name 'Main'", "\toption mac '00:00:00:00:00:00'", "\toption ip '192.168.0.10'", '', 'config host', "\toption name 'OrangePi'", "\toption mac '00:00:00:00:00:00'", "\toption ip '192.168.0.102'", '', 'config host', "\toption name 'Cablemodem_2'", "\toption mac '00:00:00:00:00:00'", "\toption ip '192.168.0.2'", '']
"""

import subprocess

rng=254
dhcp_config_route = "/etc/config/dhcp"

active_hosts = list() #Hosts detectados como activos
static_dhcp_hosts = list() #Hosts registrados en servidor DHCP para static lease

class Host(object):
	def __init__(self, ip="0", ping="0", mac="", hostname=""):
		"""Clase para cada uno de los hosts que se detecten o se vayan a procesar.
		Parámetros: ip, ping, mac, hostname ; por defecto inicializa todo con valores en blanco
		TODOS los atributos deben ser String"""

		def clean(s):
			"""Limpia strings quitando espacios en blanco y tabulaciones"""
			return s.replace(" ","").replace("\t","")

		self.ip = clean(ip)
		self.ping = clean(ping).replace("ms","")
		self.mac = clean(mac).upper()
		self.hostname = hostname


def get_data(s):
	"""Extrae el dato de interés del archivo de configuración DHCP (se presume que utiliza comillas simples y haciendo un split saldrá como el penúltimo resultado [-2])."""
	return s.split("'")[-2] # s.split("'") = ['\toption mac ', '00:00:00:00:00:00', ''] ; s.split("'")[-2] = '00:00:00:00:00:00'

def get_static_dhcp_hosts():
	"""Obtiene los hosts estáticos configurados en el servidor DHCP, leyendo el archivo de configuración del servidor DHCP. Este listado se usará para identificar más adelante a aquellos hosts que se encuentran registrados en el servidor DHCP, como hosts conocidos y de confianza."""

	dhcp_conf = open(dhcp_config_route, "r").read().splitlines() #Archivo dhcp separado por líneas

	for l_index in range(len(dhcp_conf)):
		l = dhcp_conf[l_index]

		if l == "config host": #En las 3 líneas siguientes se describirá un host
			h = Host()

			for i in range(1,4): #Obtener las 3 líneas siguientes, que incluyen las opciones name, ip y mac
				ll = dhcp_conf[l_index + i]
				
				if "option ip" in ll:
					h.ip = get_data(ll)
				elif "option mac" in ll:
					h.mac = get_data(ll)
				elif "option name" in ll:
					h.hostname = get_data(ll)
			
			static_dhcp_hosts.append(Host(ip=h.ip, mac=h.mac, hostname=h.hostname)) #Se crea nuevo objeto para que se limpie el formato de las variables (lo cual sólo sucede en el __init__ de la clase)

	print("Se han encontrado {} hosts configurados en servidor DHCP:".format( len(static_dhcp_hosts) ))
	for h in static_dhcp_hosts:
		print("    * {} [{}] ({})".format(h.ip, h.mac, h.hostname))



def get_lan_hosts():
	"""Obtiene todos los equipos conectados a la LAN según el rango designado. Utiliza pings ARP para obtener conexión si devuelven ping, tiempo de ping y MAC"""

	print("Iniciado escaneo de equipos en LAN...")
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

	print("Hay {} equipos activos:".format( len(active_hosts) ))
	known_macs = [h.mac for h in static_dhcp_hosts]
	for h in active_hosts:
		if h.mac in known_macs:
			known_status = "CONOCIDO ({})".format( [hh.hostname for hh in static_dhcp_hosts if hh.mac == h.mac][0] )
		else:
			known_status = "DESCONOCIDO"
		print("    * {} ({}ms) [{}] - {}".format(h.ip, h.ping, h.mac, known_status))

if __name__ == "__main__":
	get_static_dhcp_hosts()
	get_lan_hosts()
