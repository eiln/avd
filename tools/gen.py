#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
from ffprobe import *

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='Generate instruction stream')
	parser.add_argument('input', type=str, help="path to bitstream")
	parser.add_argument('-n', '--num', type=int, default=1, help="count")
	parser.add_argument('-a', '--all', action='store_true', help="run all")
	args = parser.parse_args()

	mode = det_format(args.input)
	if  (mode == AVD_MODE_H264):
		from avid.h264.decoder import AVDH264Decoder
		dec = AVDH264Decoder()
	elif (mode == AVD_MODE_VP9):
		from avid.vp9.decoder import AVDVP9Decoder
		dec = AVDVP9Decoder()
	else:
		raise ValueError("Not supported")

	units = dec.parse(args.input)
	n = len(units) if args.all else args.num
	for unit in units[:n]:
		inst = dec.generate(unit)
		print()
