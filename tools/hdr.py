#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
from tools.common import ffprobe, resolve_input

def parse_headers(path, num=0):
	ed = (None)
	mode = ffprobe(path)
	if (mode == "h264"):
		from avid.h264.parser import AVDH264Parser
		parser = AVDH264Parser()
		sps_list, pps_list, units = parser.parse(path, num=num)
		ed = (sps_list, pps_list)
	elif (mode == "h265"):
		from avid.h265.parser import AVDH265Parser
		parser = AVDH265Parser()
		vps_list, sps_list, pps_list, units = parser.parse(path, num=num)
		ed = (vps_list, sps_list, pps_list)
	elif (mode == "vp09"):
		from avid.vp9.parser import AVDVP9Parser
		parser = AVDVP9Parser()
		units = parser.parse(path)
	else:
		raise ValueError("Not supported")
	return units, ed

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='Show bitstream headers')
	parser.add_argument('input', type=str, help="path to bitstream")
	parser.add_argument('-s', '--start', type=int, default=0, help="start index")
	parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
	parser.add_argument('-a', '--all', action='store_true', help="run all")
	args = parser.parse_args()

	path = resolve_input(args.input)
	mode = ffprobe(path)
	units, ed = parse_headers(path)
	if  (mode == "h264" or mode == "h265"):
		if (mode == "h264"):
			sps_list, pps_list = ed
		else:
			vps_list, sps_list, pps_list = ed
			for n in range(len(vps_list)):
				if (vps_list[n]):
					print(vps_list[n])
		for n in range(len(sps_list)):
			if (sps_list[n]):
				print(sps_list[n])
		for n in range(len(pps_list)):
			if (pps_list[n]):
				print(pps_list[n])
	for unit in units[args.start:args.start+args.num]:
		print(unit)
