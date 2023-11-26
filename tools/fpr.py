#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import os
import numpy as np

from tools.common import *

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='macOS frame_params parser')
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument('-i', '--input', type=str, help="path to frame_params")
	group.add_argument('-d','--dir', type=str, help="trace dir name")
	parser.add_argument('-s', '--start', type=int, default=0, help="starting index")
	parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
	parser.add_argument('-a', '--all', action='store_true', help="run all")
	parser.add_argument('--decimal', action='store_true', help="run all")
	args = parser.parse_args()

	if (not args.decimal):
		np.set_printoptions(formatter={'int':lambda x: "0x%06x" % (x)})
	else:
		np.set_printoptions(threshold=sys.maxsize)

	if (args.dir):
		dirname = resolve_input(args.dir, isdir=True)
		paths = os.listdir(dirname)
		paths = sorted([os.path.join(dirname, path) for path in paths if "frame" in path])
		paths = paths if args.all else paths[args.start:args.start+args.num]
	else:
		paths = [args.input]

	assert(len(paths))
	fpcls = get_fpcls(paths[0])

	addrs = []
	out = []
	for i,path in enumerate(paths):
		print(i, path)
		params = open(path, "rb").read()
		fp = fpcls.parse(params)
		print(fp)

		#x = addrs.index(fp.hdr.hdr_138_ref_rvra0_addr_lsb7[0])
		#x = addrs2.index(fp.hdr.hdr_150_ref_rvra2_addr_lsb7[0])
		#x = addrs2.index(fp.hdr.hdr_11c_curr_rvra_addr_lsb7[2])
		#x = addrs3.index(fp.hdr.hdr_11c_curr_rvra_addr_lsb7[3])
		#y = [pps_addrs.index(x) for x in fp.hdr.hdr_108_pps1_tile_addr_lsb8]
		#y = addrs1.index(fp.hdr.hdr_11c_curr_rvra_addr_lsb7[1])
		#out.append(([addrs.index(x) for x in ]))

		if 1:
			x = fp.slc.slc_bd4_sps_tile_addr2_lsb8
			if (x) not in addrs:
				addrs.append(x)
			y = fp.hdr.
			z = addrs.index(x)
			out.append((i, y, z))

		if 0:
			x = fp.hdr.hdr_5c_flag
			out.append(([int(bool(x & (1 << i))) for i in range(32)]))
			#out.append((i, *[int(bool(x & (1 << i))) for i in [8, 9]]))

		#out.append((fp.slc.slc_a8c_cmd_ref_type, ))

	if 1:
		out = np.array(out) # useful for finding regressions
		print(out)
		print(", ".join([hex(x) for x in addrs]))
		#print(np.diff(out[:, 1]))
		#print(np.where(np.diff(out) > 0))
		#print(np.unique(out[:, :2]))
