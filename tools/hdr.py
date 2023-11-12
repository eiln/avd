#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
from tools.common import ffprobe, resolve_input

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='Show bitstream headers')
	parser.add_argument('input', type=str, help="path to bitstream")
	parser.add_argument('-s', '--start', type=int, default=0, help="start index")
	parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
	parser.add_argument('-a', '--all', action='store_true', help="run all")
	args = parser.parse_args()

	path = resolve_input(args.input)
	mode = ffprobe(path)
	if  (mode == "h264"):
		from avid.h264.parser import AVDH264Parser
		parser = AVDH264Parser()
		sps_list, pps_list, units = parser.parse(path, num=args.num)
		for n in range(len(sps_list)):
			if (sps_list[n]):
				print(sps_list[n])
			if (pps_list[n]):
				print(pps_list[n])
	elif (mode == "vp09"):
		from avid.vp9.parser import AVDVP9Parser
		parser = AVDVP9Parser()
		units = parser.parse(path)
	else:
		raise ValueError("Not supported")

	for unit in units[args.start:args.start+args.num]:
		print(unit)
