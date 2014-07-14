#!/usr/bin/python

# Script to automatically update Raspberry Pi PiTFT touchscreen calibration
# based on the current rotation of the screen.

# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import argparse
import os
import os.path
import re
import subprocess
import sys


# Define calibration files.
POINTERCAL_FILE = '/etc/pointercal'
XORGCAL_FILE = '/etc/X11/xorg.conf.d/99-calibration.conf'

# Define default calibration values for each rotation angle.
POINTERCAL = {}
POINTERCAL['0']   = '4315 -49 -889068 18 5873 -1043172 6553636'
POINTERCAL['90']  = '-30 -5902 22077792 4360 -105 -1038814 65536'
POINTERCAL['180'] = '-4228 73 16353030 -60 -5888 22004262 65536'
POINTERCAL['270'] = '-69 5859 -829540 -4306 3 16564590 6553636'
XORGCAL = {}
XORGCAL['0'] = """
Section "InputClass"
	Identifier      "calibration"
	MatchProduct    "stmpe-ts"
	Option  "Calibration"   "252 3861 180 3745"
	Option  "SwapAxes"      "0"
EndSection
"""
XORGCAL['90'] = """
Section "InputClass"
	Identifier      "calibration"
	MatchProduct    "stmpe-ts"
	Option  "Calibration"   "3807 174 244 3872"
	Option  "SwapAxes"      "1"
EndSection
"""
XORGCAL['180'] = """
Section "InputClass"
	Identifier      "calibration"
	MatchProduct    "stmpe-ts"
	Option  "Calibration"   "3868 264 3789 237"
	Option "SwapAxes"      "0"
EndSection
"""
XORGCAL['270'] = """
Section "InputClass"
	Identifier      "calibration"
	MatchProduct    "stmpe-ts"
	Option  "Calibration"   "287 3739 3817 207"
	Option  "SwapAxes"      "1"
EndSection
"""


def determine_rotation():
	"""Determine the rotation of the PiTFT screen by examining modprobe config."""
	# Get modprobe configuration for fbtft device.
	try:
		resp = subprocess.check_output("modprobe -c | grep 'options fbtft_device'", shell=True)
	except subprocess.CalledProcessError:
		# Error calling modprobe, return no result.
		return None
	# Look for display with name=adafruit* and rotate=<value>.
	if resp is None:
		return None
	for line in resp.splitlines():
		if re.search('name=adafruit', line, re.IGNORECASE):
			match = re.search('rotate=(\d+)', line, re.IGNORECASE)
			if match:
				# Found a rotation, return it.
				return match.group(1)
	# Couldn't find a rotation value, return nothing.
	return None

def read_file(filename):
	"""Read specified file contents and return them, or None if file isn't readable."""
	try:
		with open(filename, 'r') as infile:
			return infile.read()
	except IOError:
		return None

def write_file(filename, data):
	"""Write specified data to file.  Returns True if data was written."""
	try:
		# Check if path to file exists.  Create path if necessary.
		directory = os.path.dirname(filename)
		if not os.path.exists(directory):
			os.makedirs(directory)
		# Open file and write data.
		with open(filename, 'w') as outfile:
			outfile.write(data)
			return True
	except IOError, OSError:
		return False


# Parse command line arguments.
allowed_rotations = POINTERCAL.keys()
parser = argparse.ArgumentParser(description='Automatically set the PiTFT touchscreen calibration for both /etc/pointercal and X.Org based on the current screen rotation.')
parser.add_argument('-r', '--rotation', 
	choices=allowed_rotations, 
	required=False,
	dest='rotation',
	help='set calibration for specified screen rotation')
parser.add_argument('-f', '--force',
	required=False,
	action='store_const',
	const=True,
	default=False,
	dest='force',
	help='update calibration without prompting for confirmation')
args = parser.parse_args()

# Check that you're running as root.
if os.geteuid() != 0:
	print 'Must be run as root so calibration files can be updated!'
	print 'Try running with sudo, for example: sudo ./pitft_touch_cal.py'
	sys.exit(1)

# Determine rotation if not specified in parameters.
rotation = args.rotation
if rotation is None:
	rotation = determine_rotation()
	if rotation is None:
		# Error if rotation couldn't be determined.
		print 'Could not detect screen rotation!'
		print ''
		print 'Make sure PiTFT software is configured and run again.'
		print 'Alternatively, run with the --rotation parameter to'
		print 'specify an explicit rotation value.'
		print ''
		parser.print_help()
		sys.exit(1)

# Check rotation is allowed value.
if rotation not in allowed_rotations:
	print 'Unsupported rotation value: {0}'.format(rotation)
	print ''
	print 'Rotation must be a value of 0, 90, 180, or 270!'
	print ''
	parser.print_help()
	sys.exit(1)

print '---------------------------------'
print 'USING ROTATION: {0}'.format(rotation)
print ''

# Print current calibration values.
print '---------------------------------'
print 'CURRENT CONFIGURATION'
print ''
for cal_file in [POINTERCAL_FILE, XORGCAL_FILE]:
	cal = read_file(cal_file)
	if cal is None:
		print 'Could not determine {0} configuration.'.format(cal_file)
	else:
		print 'Current {0} configuration:'.format(cal_file)
		print cal.strip()
		print ''

# Determine new calibration values.
new_pointercal = POINTERCAL[rotation]
new_xorgcal = XORGCAL[rotation]

# Print new calibration values.
print '---------------------------------'
print 'NEW CONFIGURATION'
print ''
for cal, filename in [(new_pointercal, POINTERCAL_FILE), 
					  (new_xorgcal, XORGCAL_FILE)]:
	print 'New {0} configuration:'.format(filename)
	print cal.strip()
	print ''

# Confirm calibration change with user.
if not args.force:
	confirm = raw_input('Update current configuration to new configuration? [y/N]: ')
	print '---------------------------------'
	print ''
	if confirm not in ['y', 'Y', 'yes', 'YES']:
		print 'Exiting without updating configuration.'
		sys.exit(0)

# Change calibration.
status = 0
for cal, filename in [(new_pointercal, POINTERCAL_FILE), 
					  (new_xorgcal, XORGCAL_FILE)]:
	if not write_file(filename, cal):
		print 'Failed to update {0}'.format(filename)
		status = 1
	else:
		print 'Updated {0}'.format(filename)
sys.exit(status)
