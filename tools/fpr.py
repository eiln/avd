#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import os
import numpy as np
np.set_printoptions(formatter={'int':lambda x: "0x%06x" % (x)})

import struct
from tools.common import resolve_input

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='macOS frame_params parser')
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument('-i', '--input', type=str, help="path to frame_params")
	group.add_argument('-d','--dir', type=str, help="trace dir name")
	parser.add_argument('-s', '--start', type=int, default=0, help="starting index")
	parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
	parser.add_argument('-a', '--all', action='store_true', help="run all")
	args = parser.parse_args()

	if (args.dir):
		dirname = resolve_input(args.dir, isdir=True)
		paths = os.listdir(dirname)
		paths = sorted([os.path.join(dirname, path) for path in paths if "frame" in path])
		paths = paths if args.all else paths[args.start:args.start+args.num]
	else:
		paths = [args.input]

	# determine mode
	_, mode = struct.unpack("<II", open(paths[0], "rb").read()[:8])
	if  (mode == 1):
		from avid.h264.fp import AVDH264V3FrameParams
		fpcls = AVDH264V3FrameParams
	elif (mode == 2):
		from avid.vp9.fp import AVDVP9V3FrameParams
		fpcls = AVDVP9V3FrameParams
	else:
		raise ValueError("Not supported")

	out = []
	for i,path in enumerate(paths):
		print(path)
		params = open(path, "rb").read()
		fp = fpcls.parse(params)
		print(fp)
		#out.append((fp.hdr.hdr_48_incr_addr, fp.hdr.hdr_4c_incr_size))
	#out = np.array(out) # useful for finding regressions
	#print(out)
