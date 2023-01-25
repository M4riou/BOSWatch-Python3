#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

Plugin to control Philips hue lights and switches

@author: Fabian Kessler, Marius Kortmann

@requires: none
"""

#
# Imports
#
import logging # Global logger
import json
import threading
import requests
import time
import io

from enum import Enum

from includes import globalVars  # Global variables

# Helper function, uncomment to use
from includes.helper import timeHandler
#from includes.helper import wildcardHandler
from includes.helper import configHandler

class Scene(str, Enum):
	BRIGHT = '{"bri": 254, "xy": [0.4575, 0.4099], "ct":366}' # "hue": 8402,"sat": 140
	CONCENTRATE = '{"bri": 254, "xy": [0.3691, 0.3719], "ct":230}' # "hue": 39392,"sat": 13
	RELAX = '{"bri": 144, "xy": [0.5016, 0.4151], "ct":443}' # "hue": 7676,"sat": 199

##
#
# onLoad (init) function of plugin
# will be called one time by the pluginLoader on start
#
def onLoad():
	"""
	While loading the plugins by pluginLoader.loadPlugins()
	this onLoad() routine is called one time for initialize the plugin
	@requires:  nothing
	@return:    nothing
	@exception: Exception if init has an fatal error so that the plugin couldn't work
	"""
	try:
		if configHandler.checkConfig("hue"):

			bridgeip = globalVars.config.get("hue", "bridgeip")
			apikey = globalVars.config.get("hue", "apikey")

			if (bridgeip == ""):
				logging.error("No bridgeip configured!")
				raise ValueError("No bridgeip configured!")
			elif (bridgeip != "") and (apikey == ""):
				import platform

				print("\nCouldn't find Philips hue API key. Please press the link button on the Bridge!\n")
				url = "http://" + bridgeip + "/api"
				device_data = {"devicetype":"BOSWatch#{0}".format(platform.node())}
				key_created = False

				for i in range(1, 7):
					time.sleep(10)
					print("Trying to register at hue bridge({0}). Attempt {1}/6...".format(bridgeip, i))
					registration_response = requests.post(url, json=device_data)
					try:
						if "error" in registration_response.json()[0]:
							print("Couldn't register at designated hue bridge. Please press the link button or check the configured IP!")
						else:
							apikey = registration_response.json()[0]["success"]["username"]

							key_created = True

							print("Successfully registered at hue bridge under the name " + device_data["devicetype"])
							print("API Key: " + apikey)

							logging.info("Successfully registered at hue bridge under the name " + device_data["devicetype"])

							hue_config = globalVars.config["hue"]
							hue_config["apikey"] = apikey

							lines = []
							with io.open(globalVars.script_path+"/config/config.ini", "r", encoding="utf8") as config:
								lines = config.readlines()

							found_hue = False
							for i, line in enumerate(lines):
								print(found_hue)
								if "[hue]" in line:
									found_hue = True
								elif found_hue and ("apikey =" in line):
									found_hue = False
									lines[i] = "apikey = {0}\n".format(apikey)

									with io.open(globalVars.script_path+"/config/config.ini", "w", encoding="utf8") as config:
										config.writelines(lines)

									break

							break
					except:
						logging.error("Error trying to reach hue bridge({0})".format(bridgeip))
						logging.debug("Error trying to reach hue bridge({0})".format(bridgeip), exc_info=True)

				if key_created == False:
					logging.error("Couldn't register at designated hue bridge({0})!".format(bridgeip))
					# Raise an Error to ensure that the Plugin won't be loaded
					raise RuntimeError("Couldn't register at designated hue bridge({0})!".format(bridgeip))

			if globalVars.config.getboolean("hue", "generate_info_file"):
				url = "http://" + bridgeip + "/api/" + apikey

				response = (requests.get(url)).json()

				with io.open(globalVars.script_path + '/plugins/hue/hue_info.txt', 'w', encoding='utf8') as info_file:

					info_file.write("Lights and Groups saved on Bridge: " + response["config"]["name"] + " -- " + timeHandler.curtime(timeStr="%d.%m.%Y %H:%M"))

					info_file.write("\n\nLights:")
					for light in response["lights"]:
						info_file.write("\n\t" + response["lights"][light]["name"] + " - deviceid: " + light)

					info_file.write("\n\nGroups:")
					for group in response["groups"]:
						info_file.write("\n\t" + response["groups"][group]["name"] + " - groupid: " + group)
	except:
		logging.error("Error trying to load hue Plugin!")
		logging.debug("Error trying to load hue Plugin!", exc_info=True)
		raise

# Crude implementation of math.isClose() for Python2 backwards compatibility
def number_isClose(a, b, rel_tol=1e-09, abs_tol=0.0):
	return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

# blink function passed to each thread
def hue_blink(target: str, url, device_type, data_on, data_off, blink, repeat, timeon, timeoff, keepon):
	data_on_json = json.loads(data_on)
	data_off_json = json.loads(data_off)

	blink_data_on = data_on
	blink_data_off = data_off

	# dont turn lights off completely, to avoid disaster in the dark
	if not data_off_json["on"]:
		blink_data_off_json = data_off_json
		blink_data_off_json["on"] = True
		blink_data_off_json["bri"] = 50
		blink_data_off = json.dumps(blink_data_off_json)

	# There are different types of hue devices, each with different capabilities.
	# Check the light type and adjust commands accordingly.
	if device_type == "color temperature light":

		# Check if selected are lights already at the desired scene and change the brightness to make
		# the blinking noticeable
		if (number_isClose(data_on_json["ct"], data_off_json["ct"], rel_tol=0.05) and
			number_isClose(data_on_json["bri"], data_off_json["bri"], rel_tol=0.2)):

			blink_data_on_json = data_on_json
			if data_on_json["bri"] > 205:
				blink_data_on_json["bri"] = max(int(data_on_json["bri"]/2), 1)
			else:
				blink_data_on_json["bri"] = min(int(data_on_json["bri"]*2), 254)

			blink_data_on = json.dumps(blink_data_on_json)

	elif device_type == (device_type == "color light") or (device_type == "extended color light"):

		# Check if selected are lights already at the desired scene and change the brightness to make
		# the blinking noticeable
		if (number_isClose(data_on_json["xy"][0], data_off_json["xy"][0], rel_tol=0.05) and
			number_isClose(data_on_json["xy"][1], data_off_json["xy"][1], rel_tol=0.05) and
			number_isClose(data_on_json["bri"], data_off_json["bri"], rel_tol=0.2)):

			blink_data_on_json = data_on_json
			if data_on_json["bri"] > 205:
				blink_data_on_json["bri"] = max(int(data_on_json["bri"]/2), 1)
			else:
				blink_data_on_json["bri"] = min(int(data_on_json["bri"]*2), 254)

			blink_data_on = json.dumps(blink_data_on_json)

	elif device_type == "dimmable light":

		# Check if selected are lights already at the desired scene and change the brightness to make
		# the blinking noticeable
		if (number_isClose(data_on_json["bri"], data_off_json["bri"], rel_tol=0.2)):

			blink_data_on_json = data_on_json
			if data_on_json["bri"] > 205:
				blink_data_on_json["bri"] = max(int(data_on_json["bri"]/2), 1)
			else:
				blink_data_on_json["bri"] = min(int(data_on_json["bri"]*2), 254)

			blink_data_on = json.dumps(blink_data_on_json)
	else:

		blink_data_off = data_off

	if blink:
		for _ in range(repeat):
			requests.put(url, data=blink_data_on)
			logging.debug("{0}: on for {1} seconds".format(target, timeon))
			time.sleep(timeon)
			requests.put(url, data=blink_data_off)
			logging.debug("{0}: off for {1} seconds".format(target, timeoff))
			time.sleep(timeoff)
	elif keepon >= 0:
		keepon = keepon + repeat * (timeon + timeoff)

	if keepon > 0:
		logging.debug("{0}: switch to on and wait for keepon to expire".format(target))
		requests.put(url, data=data_on)
		logging.debug("{0}: keep on for {1} seconds".format(target, keepon))
		time.sleep(keepon)
		requests.put(url, data=data_off)
	elif keepon == 0:
		logging.debug("{0}: switch to off and exit plugin".format(target))
		requests.put(url, data=data_off)
	else:
		logging.debug("{0}: switch to on and exit plugin".format(target))
		requests.put(url, data=data_on)

##
#
# Main function of plugin
# will be called by the alarmHandler
#
def run(typ,freq,data):
	"""
	This function is the implementation of the Plugin.
	If necessary the configuration hast to be set in the config.ini.
	@type    typ:  string (FMS|ZVEI|POC)
	@param   typ:  Typ of the dataset
	@type    data: map of data (structure see readme.md in plugin folder)
	@param   data: Contains the parameter for dispatch
	@type    freq: string
	@keyword freq: frequency of the SDR Stick
	@requires:  If necessary the configuration hast to be set in the config.ini.
	@return:    nothing
	@exception: nothing, make sure this function will never thrown an exception
	"""
	try:
		if configHandler.checkConfig("hue"): #read and debug the config
			#for debugging
			"""logging.debug(globalVars.config.get("hue", "bridgeip"))
			logging.debug(globalVars.config.get("hue", "deviceid"))
			logging.debug(globalVars.config.get("hue", "apikey"))
			logging.debug(globalVars.config.getint("hue", "repeat"))
			logging.debug(globalVars.config.getint("hue", "timeon"))
			logging.debug(globalVars.config.getint("hue", "timeoff"))
			logging.debug(globalVars.config.getint("hue", "keepon"))"""

			########## User Plugin CODE ##########
			if typ == "FMS":
				logging.warning("%s not supported", typ)
			elif typ == "ZVEI":
				logging.warning("%s not supported", typ)
			elif typ == "POC":
				#logging.warning("%s not supported", typ)
				logging.debug("POC received")
				bridgeip = globalVars.config.get("hue", "bridgeip")
				apikey = globalVars.config.get("hue", "apikey")
				repeat = globalVars.config.getint("hue", "repeat")
				timeon = globalVars.config.getint("hue", "timeon")
				timeoff = globalVars.config.getint("hue", "timeoff")
				keepon = globalVars.config.getint("hue", "keepon")
				force_off = globalVars.config.getboolean("hue", "force_off")
				data_on = '{"on":true}'
				data_off = '{"on":false}'

				# List of Strings which are to be considered as True
				string_true = ['true', '1', 'on', 'yes']

				devices = globalVars.config.get("hue", "deviceid").replace(" ", "").split(",")
				device_dict = {}
				# Check if the Config String is empty
				if devices[0] != "":
					# Parse the String passed from the Config as dict to allow proper iteration and key matching
					device_dict = dict((device_id.strip(), device_blink.strip().lower() in string_true)
											for device_id, device_blink in (device.split('-')
														for device in devices))

				groups = globalVars.config.get("hue", "groupid").replace(" ", "").split(",")
				group_dict = {}
				# Check if the Config String is empty
				if groups[0] != "":
					# Parse the String passed from the Config as dict to allow proper iteration and key matching
					group_dict = dict((group_id.strip(), group_blink.strip().lower() in string_true)
											for group_id, group_blink in (group.split('-')
														for group in groups))

				scene = None
				if globalVars.config.has_option("hue","scene"):
					try:
						scene = Scene[globalVars.config.get("hue", "scene").upper()]
					except KeyError:
						scene = None
						logging.error("Selected Scene is not a valid option!")
					except:
						raise

				current_states = requests.get("http://" + bridgeip + "/api/" + apikey).json()

				# Check if at least one Device has been selected
				if device_dict:
					for d_id in device_dict.keys():

						device_type = (current_states["lights"][d_id]["type"]).lower()

						# Check if a thread to control the selected Device is already active
						thread_name = "BOSWatch-hue-light_{0}".format(d_id)
						active_threads = [thread.name for thread in threading.enumerate()]
						if thread_name not in active_threads:

							# There are different types of hue devices, each with different capabilities.
							# Check the light type and adjust commands accordingly.
							if device_type == "color temperature light":

								# Decide wether to turn the Device off or return to the state before the alarm
								if force_off:
									current_device_state = current_states["lights"][d_id]["state"]
									current_scene_json = {"on": False, "bri": current_device_state["bri"], "ct": current_device_state["ct"]}
									data_off = json.dumps(current_scene_json)
								else:
									current_device_state = current_states["lights"][d_id]["state"]
									current_scene_json = {"on": current_device_state["on"], "bri": current_device_state["bri"], "ct": current_device_state["ct"]}
									data_off = json.dumps(current_scene_json)

								# Change light Brightness/Color/Temperature if a scene has been selected
								if scene is not None:
									data_on_json = json.loads(data_on)
									scene_json = json.loads(scene)

									del scene_json['xy']

									data_on_json.update(scene_json)

									data_on = json.dumps(data_on_json)
								else:
									data_on_json = json.loads(data_on)
									scene_json = current_states["lights"][d_id]["state"]

									del scene_json['on']

									del scene_json['hue']
									del scene_json['sat']
									del scene_json['effect']
									del scene_json['xy']

									del scene_json['alert']
									del scene_json['colormode']
									del scene_json['mode']
									del scene_json['reachable']

									data_on_json.update(scene_json)

									data_on = json.dumps(data_on_json)

							elif (device_type == "color light") or (device_type == "extended color light"):

								# Decide wether to turn the Device off or return to the state before the alarm
								if force_off:
									current_device_state = current_states["lights"][d_id]["state"]
									current_scene_json = {"on": False, "bri": current_device_state["bri"], "xy": current_device_state["xy"]}
									data_off = json.dumps(current_scene_json)
								else:
									current_device_state = current_states["lights"][d_id]["state"]
									current_scene_json = {"on": current_device_state["on"], "bri": current_device_state["bri"], "xy": current_device_state["xy"]}
									data_off = json.dumps(current_scene_json)

								# Change light Brightness/Color/Temperature if a scene has been selected
								if scene is not None:
									data_on_json = json.loads(data_on)
									scene_json = json.loads(scene)

									del scene_json['ct']

									data_on_json.update(scene_json)

									data_on = json.dumps(data_on_json)
								else:
									data_on_json = json.loads(data_on)
									scene_json = current_states["lights"][d_id]["state"]

									del scene_json['on']

									del scene_json['hue']
									del scene_json['sat']
									del scene_json['effect']
									del scene_json['ct']

									del scene_json['alert']
									del scene_json['colormode']
									del scene_json['mode']
									del scene_json['reachable']

									data_on_json.update(scene_json)

									data_on = json.dumps(data_on_json)

							elif device_type == "dimmable light":

								# Decide wether to turn the Device off or return to the state before the alarm
								if not force_off:
									current_device_state = current_states["lights"][d_id]["state"]
									current_scene_json = {"on": current_device_state["on"]}
									data_off = json.dumps(current_scene_json)

								# Change light Brightness/Color/Temperature if a scene has been selected
								if scene is not None:
									data_on_json = json.loads(data_on)
									scene_json = json.loads(scene)

									del scene_json['ct']
									del scene_json['xy']

									data_on_json.update(scene_json)

									data_on = json.dumps(data_on_json)
								else:
									data_on_json = json.loads(data_on)
									scene_json = current_states["lights"][d_id]["state"]

									del scene_json['on']

									del scene_json['hue']
									del scene_json['sat']
									del scene_json['effect']
									del scene_json['xy']
									del scene_json['ct']
									del scene_json['alert']
									del scene_json['colormode']
									del scene_json['mode']
									del scene_json['reachable']

									data_on_json.update(scene_json)

									data_on = json.dumps(data_on_json)

							else:

								# Decide wether to turn the Device off or return to the state before the alarm
								if not force_off:
									current_device_state = current_states["lights"][d_id]["state"]
									current_scene_json = {"on": current_device_state["on"]}
									data_off = json.dumps(current_scene_json)

							# Create Thread and start it
							url = "http://" + bridgeip + "/api/" + apikey + "/lights/" + d_id + "/state"
							target_device = "LightID {0}".format(d_id)
							thread_args = (target_device, url, device_type, data_on, data_off, device_dict[d_id], repeat, timeon, timeoff, keepon)
							t = threading.Thread(name=thread_name, target=hue_blink, args=thread_args)
							t.start()

				# Check if at least one Group has been selected
				if group_dict:
					for g_id in group_dict.keys():

						# Check if a thread to control the selected Group is already active
						thread_name = "BOSWatch-hue-group_{0}".format(g_id)
						active_threads = [thread.name for thread in threading.enumerate()]
						if thread_name not in active_threads:

							# Decide wether to turn the Group off or return to the state before the alarm
							if force_off:
								current_group_state = current_states["groups"][g_id]["action"]
								current_scene_json = {"on": False, "bri": current_group_state["bri"], "xy": current_group_state["xy"]}
								data_off = json.dumps(current_scene_json)
							else:
								current_group_state = current_states["groups"][g_id]["action"]
								current_scene_json = {"on": current_group_state["on"], "bri": current_group_state["bri"], "xy": current_group_state["xy"]}
								data_off = json.dumps(current_scene_json)

							# Change light Brightness/Color/Temperature if a scene has been selected
							if scene is not None:
								data_on_json = json.loads(data_on)
								scene_json = json.loads(scene)

								del scene_json["ct"]

								data_on_json.update(scene_json)

								data_on = json.dumps(data_on_json)
							else:
								data_on_json = json.loads(data_on)
								scene_json = current_states["lights"][d_id]["state"]

								del scene_json['on']

								del scene_json['hue']
								del scene_json['sat']
								del scene_json['effect']
								del scene_json['ct']

								del scene_json['alert']
								del scene_json['colormode']
								del scene_json['mode']
								del scene_json['reachable']

								data_on_json.update(scene_json)

								data_on = json.dumps(data_on_json)

							# Create Thread and start it
							url = "http://" + bridgeip + "/api/" + apikey + "/groups/" + g_id + "/action"
							target_device = "GroupID {0}".format(g_id)
							thread_args = (target_device, url, data_on, data_off, group_dict[g_id], repeat, timeon, timeoff, keepon)
							t = threading.Thread(name=thread_name, target=hue_blink, args=thread_args)
							t.start()

			else:
				logging.warning("Invalid Typ: %s", typ)
			########## User Plugin CODE ##########

	except:
		logging.error("unknown error")
		logging.debug("unknown error", exc_info=True)
