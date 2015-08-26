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


if len(sys.argv) < 2:
	print("usage bluefence.py <btaddr>")
	sys.exit(1)

btaddr= sys.argv[1]
btInRange=True
screenLocked=False
counter=0

print "Initializing device..." 

try:
	if bluetooth.lookup_name(btaddr,1):
		print 'OK: Your device is active.'

	initialize =  bluetooth.lookup_name(btaddr,timeout=10)
	print 'OK: "',initialize,'" found.'
	
	while True:
		who =  bluetooth.lookup_name(btaddr,timeout=2)

		if who:

			status = 'device found'
			btInRange=True
			counter=0
			os.system(IF_BT_BACK)

		else:
			
			counter+=1
			status = 'device lost '

		if counter > MAX_MISSED:
			os.system(IF_BT_GONE)
			status = 'MATI!'
			counter = 0
			btInRange=False

		time.sleep(DEFAULT_TIMEOUT)

		print status, ' | ', counter, ' | ', btInRange, ' | ', time.strftime('%H:%M:%S')

except:
	print('ER: Your device is not ready')