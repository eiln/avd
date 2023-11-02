#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import os
import numpy as np
np.set_printoptions(formatter={'int':lambda x: "0x%05x" % (x)})

from avid.fp import *
from avid.h264.fp import *

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='macOS frame_params parser')
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument('-i', '--path', type=str, help="path to frame_params")
	group.add_argument('-d','--dir', type=str, help="frame_params dir name")
	parser.add_argument('-p','--prefix', type=str, default="", help="dir prefix")
	parser.add_argument('-s', '--start', type=int, default=0, help="starting index")
	parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
	parser.add_argument('-a', '--all', action='store_true', help="run all")
	args = parser.parse_args()

	if args.dir:
		paths = os.listdir(os.path.join(args.prefix, args.dir))
		paths = sorted([os.path.join(args.prefix, args.dir, path) for path in paths if "param" in path or "frame" in path])
		paths = paths if args.all else paths[args.start:args.start+args.num]
	else:
		paths = [args.path]

	out = []
	for path in paths:
		params = open(path, "rb").read()
		fp = AvdH264V3FrameParams.parse(params)
		print(fp)
		out.append((fp.hdr.hdr_c0_curr_ref_addr_lsb7[0],))
		print("="*80)
	out = np.array(out) # useful for finding regressions
	print(out)
