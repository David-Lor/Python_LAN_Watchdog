#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""	PING A TODAS LAS IPs DE LAN
* Objeto clase Host contiene IP, Ping y MAC (strings)
* Se escanea con ARPING todas las IPs (devuelve el tiempo y la MAC). Hay que ignorar el localhost porque no hace ping con arping.
* Se devuelve al final listado de IPs encontradas con sus pings y macs
* Se determina si un host (ip y mac) es Conocido (estaba definido en archivo config DHCP [static dhcp leases]) o si es Desconocido
* Creación de bucle (2 tiempos: detectar equipos y reanalizar archivo DHCP)
* Envía por Telegram notificaciones cuando se detecta un nuevo host desconocido.
"""

import subprocess, telebot
from time import sleep

rng = 254
lan_watchdog_freq = 2	#Tiempos en minutos
dhcp_config_route = "/home/david/Nextcloud/Codigos/Python/MonitorRed/lan_watchdog_LEDE/dhcp"
bot_token = ""
bot_auth = 000000

bot = telebot.TeleBot(bot_token, threaded=False)

active_hosts = list() #Hosts detectados como activos
static_dhcp_hosts = list() #Hosts registrados en servidor DHCP para static lease

def clean(s, mac=False):
	"""Limpia string quitando espacios en blanco y tabulaciones. Opción adicional MAC para hacer un uppercase"""
	s = s.replace(" ","").replace("\t","")
	if mac:
		s = s.upper()
	return s

class Host(object):
	def __init__(self, ip="0", ping="0", mac="", hostname=""):
		"""Clase para cada uno de los hosts que se detecten o se vayan a procesar.
		Parámetros: ip, ping, mac, hostname ; por defecto inicializa todo con valores en blanco
		TODOS los atributos deben ser String"""

		self.ip = clean(ip)
		self.ping = clean(ping).replace("ms","")
		self.mac = clean(mac, mac=True)
		self.hostname = hostname


def get_data(s):
	"""Extrae el dato de interés del archivo de configuración DHCP (se presume que utiliza comillas simples y haciendo un split saldrá como el penúltimo resultado [-2])."""
	return s.split("'")[-2] # s.split("'") = ['\toption mac ', '00:00:00:00:00:00', ''] ; s.split("'")[-2] = '00:00:00:00:00:00'

def get_static_dhcp_hosts():
	"""Obtiene los hosts estáticos configurados en el servidor DHCP, leyendo el archivo de configuración del servidor DHCP. Este listado se usará para identificar más adelante a aquellos hosts que se encuentran registrados en el servidor DHCP, como hosts conocidos y de confianza."""

	dhcp_conf = open(dhcp_config_route, "r").read().splitlines() #Archivo dhcp separado por líneas
	static_dhcp_hosts_macs = tuple(h.mac for h in static_dhcp_hosts) #Lista de MACs de equipos activos
	static_dhcp_hosts_now = list()

	for l_index in range(len(dhcp_conf)):
		l = dhcp_conf[l_index]

		if l == "config host": #En las 3 líneas siguientes se describirá un host
			for i in range(1,4): #Obtener las 3 líneas siguientes, que incluyen las opciones name, ip y mac
				ll = dhcp_conf[l_index + i]
				if "option ip" in ll:
					ip = get_data(ll)
				elif "option mac" in ll:
					mac = get_data(ll)
				elif "option name" in ll:
					hostname = get_data(ll)
			static_dhcp_hosts_now.append( Host(ip=ip, mac=mac, hostname=hostname) )
	
	print("Se han encontrado {} hosts configurados en servidor DHCP:".format( len(static_dhcp_hosts_now) ))
	for h in sorted( static_dhcp_hosts_now, key=lambda x: int( x.ip.split(".")[-1] ) ):
		print( "    * {} [{}] ({})".format(h.ip, h.mac, h.hostname) )
		if h.mac not in static_dhcp_hosts_macs: #Añadir nuevos equipos
			static_dhcp_hosts.append(h)
	
	static_dhcp_hosts_now_macs = tuple(h.mac for h in static_dhcp_hosts_now)
	for h in static_dhcp_hosts: #Eliminar static leases borrados de archivo config
		if h.mac not in static_dhcp_hosts_now_macs:
			print("Host {} ({}) eliminado de configuración static lease de DHCP".format(h.hostname, h.mac))
			static_dhcp_hosts.remove(h)


def get_lan_hosts():
	"""Obtiene todos los equipos conectados a la LAN según el rango designado. Utiliza pings ARP para obtener conexión si devuelven ping, tiempo de ping y MAC"""

	print("\nIniciado escaneo de equipos en LAN...")
	active_hosts_now = list()
	active_hosts_macs = tuple(h.mac for h in active_hosts)
	static_dhcp_hosts_macs = tuple(h.mac for h in static_dhcp_hosts)
	
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
			known = ""
		else: #Host online:
			active_hosts_now.append( Host(ip=dest, ping=ping, mac=mac) )
			try:
				known = " ({})".format( next(h.hostname for h in static_dhcp_hosts if h.mac == mac) )
			except:
				known = " (Desconocido)"

		print( "IP {} -> {}{}".format(dest, ping, known) )
	
	print("")
	active_hosts_now_macs = tuple(h.mac for h in active_hosts_now)
	for h in active_hosts: #Equipos desconectados
		if h.mac not in active_hosts_now_macs:
			print( "Equipo {} [{}] ({}) desconectado".format(h.ip, h.mac, h.hostname) )
			active_hosts.remove(h)
	
	print("Se han encontrado {} equipos activos:".format( len(active_hosts_now) ))
	for h in active_hosts_now: #Equipos conectados
		if h.mac in static_dhcp_hosts_macs: #Equipo conocido
			h.hostname = next(hh.hostname for hh in static_dhcp_hosts if hh.mac == h.mac)
			known = True
		else: #Equipo desconocido
			h.hostname = "Desconocido"
			known = False
		
		if h.mac not in active_hosts_macs: #Equipo activo nuevo
			active_hosts.append(h)
			new_out = " *nuevo*"
			
			if not known: #Equipo desconocido y nuevo: Notificar por Telegram
				bot.send_message( bot_auth,"Nuevo equipo desconocido conectado:\n\t* IP: {}\n\t* MAC: {}".format(h.ip, h.mac) )
		
		else: #Equipo activo que ya estaba activo previamente
			new_out = ""

		print( "    * {} ({} ms) [{}] - {}{}".format(h.ip, h.ping, h.mac, h.hostname, new_out) )
		
		


if __name__ == "__main__":
	while True:
		try:
			get_static_dhcp_hosts()
			get_lan_hosts()
			sleep(lan_watchdog_freq*60)
		except KeyboardInterrupt:
			break
