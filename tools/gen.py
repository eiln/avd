#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
from avid.h264.decoder import AVDH264Decoder

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='Generate instruction stream')
	parser.add_argument('path', type=str, help="path to .h264")
	parser.add_argument('-n', '--num', type=int, default=1, help="count")
	parser.add_argument('-a', '--all', action='store_true')
	args = parser.parse_args()

	dec = AVDH264Decoder()
	units = dec.parse(args.path)
	n = len(units) if args.all else args.num
	for unit in units[:n]:
		inst = dec.generate(unit)
