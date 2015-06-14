#!/usr/bin/python
# -*- coding: cp1252 -*-

"""
Search for decode string and call the right decoder function

@author: Jens Herrmann

@requires: none
"""

import logging # Global logger

def decode(freq, decoded):
	"""
	Search for decode string and call the right decoder function

	@type    freq: string
	@param   freq: frequency of the SDR Stick
	@type    decoded: string
	@param   decoded: RAW Information from Multimon-NG
	
	@return:    nothing
	@exception: Exception if decoder File call failed
	"""
	try:
		# FMS Decoder Section    
		# check FMS: -> check CRC -> validate -> check double alarm -> log
		if "FMS:" in decoded:   
			logging.debug("recieved FMS")
			from includes.decoders import fms
			fms.decode(freq, decoded)

		# ZVEI Decoder Section
		# check ZVEI: -> validate -> check double alarm -> log     
		elif "ZVEI2:" in decoded:
			logging.debug("recieved ZVEI")			
			from includes.decoders import zvei
			zvei.decode(freq, decoded)
			
		# For POCSAG we have to ignore the multimon-ng line "Enabled demodulators:"
		elif "Enabled demodulators:" in decoded:
			pass
			
		# POCSAG Decoder Section
		# check POCSAG -> validate -> check double alarm -> log      
		elif "POCSAG" in decoded:
			logging.debug("recieved POCSAG")				
			from includes.decoders import poc
			poc.decode(freq, decoded)
			
	except:
		logging.exception("cannot start decoder")