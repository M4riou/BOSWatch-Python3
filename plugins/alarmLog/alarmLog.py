#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
alarmLog-Plugin to Log all messages to a File

@author: Marius Kortmann

@requires:
"""

import logging # Global logger
import io
import os

from includes import globalVars # Global variables

from includes.helper import timeHandler
from includes.helper import configHandler
from includes.helper import wildcardHandler

# local variables
alarmlog_path = globalVars.log_path + 'alarms/'

##
#
# onLoad (init) function of plugin
# will be called one time by the pluginLoader on start
#
def onLoad():

    try:
        global alarmlog_path
        if configHandler.checkConfig("alarmLog"):
            if globalVars.config.has_option("alarmLog","alarmlog_path"):
                alarmlog_path = globalVars.config.get("alarmLog","alarmlog_path") + 'alarms/'

            if not os.path.exists(alarmlog_path):
                os.makedirs(alarmlog_path)
    except:
        logging.error("Initialization Error")
        logging.debug("Initialization Error", exc_info=True)
        raise

    return

def onClose():

    return

def log(alarmMessage):

    try:
        global alarmlog_path
        with io.open(alarmlog_path + 'alarms-%s.txt' %timeHandler.curtime("%Y_%m_%d", timestamp=""), 'a', encoding='utf8') as f:
            f.write(alarmMessage + '\n')
    except:
        logging.error("Writing Alarm to File failed")
        logging.debug("Writing Alarm to File failed", exc_info=True)
        raise

def run(typ, freq, data):

    try:
        if configHandler.checkConfig("alarmLog"): #read and debug the config
            if typ == "FMS":
                logging.debug("Start FMS to File")
                try:
                    alarmMessage = globalVars.config.get("alarmLog", "fms_message")
                    alarmMessage = wildcardHandler.replaceWildcards(alarmMessage, data)

                    log(alarmMessage)
                except:
                    logging.error("%s to File failed", typ)
                    logging.debug("%s to File failed", typ, exc_info=True)
                    return
            elif typ == "ZVEI":
                logging.debug("Start ZVEI to File")
                try:
                    alarmMessage = globalVars.config.get("alarmLog", "zvei_message")
                    alarmMessage = wildcardHandler.replaceWildcards(alarmMessage, data)

                    log(alarmMessage)
                except:
                    logging.error("%s to File failed", typ)
                    logging.debug("%s to File failed", typ, exc_info=True)
                    return
            elif typ == "POC":
                logging.debug("Start POC to File")
                try:
                    alarmMessage = globalVars.config.get("alarmLog", "poc_message")
                    alarmMessage = wildcardHandler.replaceWildcards(alarmMessage, data)

                    log(alarmMessage)
                except:
                    logging.error("%s to File failed", typ)
                    logging.debug("%s to File failed", typ, exc_info=True)
                    return
            else:
                logging.warning("Invalid Type: %s", typ)
    except:
        # something very mysterious
        logging.error("unknown error")
        logging.debug("unknown error", exc_info=True)
