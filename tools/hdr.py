#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
from avid.h264.parser import AVDH264Parser

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='Show H.264 bitstream headers')
	parser.add_argument('path', type=str, help="path to *.h264")
	parser.add_argument('-s', '--start', type=int, default=0, help="start index")
	parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
	parser.add_argument('-a', '--all', action='store_true')
	args = parser.parse_args()

	parser = AVDH264Parser()
	sps_list, pps_list, units = parser.parse(args.path)
	for n in range(len(sps_list)):
		if (sps_list[n]):
			print(sps_list[n])
		if (pps_list[n]):
			print(pps_list[n])
	out = []
	for unit in units[args.start:args.start+args.num]:
		print(unit)
