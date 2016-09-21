#!/usr/bin/python

# BlueFence version 0.1 (Prototype)
# Author: Yeni Setiawan
# Email	: sandalian@protonmail.ch
# Blog	: www.sandalian.com

import bluetooth
import time
import sys
import os

DEFAULT_TIMEOUT = 5                                 # time between searches for device in seconds 
IF_BT_GONE = 'xrandr --output eDP1 --brightness 0' # The command to run when the device is out of range
IF_BT_BACK = 'xrandr --output eDP1 --brightness 1' # The command to run when the device is back in range
MAX_MISSED = 3    
VERBOSE = True

if len(sys.argv) < 2:
	print("usage bluefence.py <btaddr>")
	sys.exit(1)

btaddr= sys.argv[1]
btInRange=True
screenLocked=False
counter=0

if VERBOSE:
	print "Identifying device..." 
	print bluetooth.lookup_name(btaddr,timeout=10)

try:
	if bluetooth.lookup_name(btaddr,timeout=10):
		if VERBOSE:
			print 'OK: Your device is active.'
	else:
		if VERBOSE:
			print 'Your device is inactive.'
			print 'Activate your device and try again.'
		sys.exit(1)

	identify =  bluetooth.lookup_name(btaddr,timeout=5).strip()

	if identify:
		if VERBOSE:
			print 'OK: Found',identify.strip()
	else:
		if VERBOSE:
			print 'ER: No device found.'

	while True:
		who =  bluetooth.lookup_name(btaddr,timeout=2)

		if who:
			# if previously our of range, say welcome back and do the job
			if btInRange == False:
				status = 'WELCOME BACK!'
				os.system(IF_BT_BACK)
			else:
				status = 'near'

			# okay, device is in range
			btInRange=True

			# reset away counter
			counter=0

		else:
			# oops, device is away. start counter 
			status = 'away'
			counter+=1

		# this what would happen if device is away after MAX_MISSED times
		if counter > MAX_MISSED:

			# if previously near, do this when away
			if btInRange==True:
				os.system(IF_BT_GONE)

			# update status, reset counter, say that device is away
			status = 'MATI!'
			counter = 0
			btInRange=False

		time.sleep(DEFAULT_TIMEOUT)

		firstCheck+=1

		#if VERBOSE:
		print status, '|', counter, '|', btInRange, '|', time.strftime('%H:%M:%S')

except:
	print('ER: Bluetooth on PC is not active.')
