#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import os
from avid.utils import *
from avid.vp9.decoder import AVDVP9Decoder
from avid.vp9.fp import *

def test(fp0, fp1, args):
	cands = [
	"hdr_28_height_width_shift3",
	#"hdr_2c_sps_param",
	"hdr_30_cmd_start_hdr",
	"hdr_34_const_20",
	"hdr_38_height_width_shift3",
	#"hdr_40_flags1_pt1",

	"hdr_e0_const_240",
	"hdr_104_probs_addr_lsb8",
	"hdr_118_pps0_tile_addr_lsb8",
	"hdr_108_pps1_tile_addr_lsb8",

	#"hdr_48_flags2_pt1",
	#"hdr_44_flags1_pt2",
	#"hdr_4c_flags2_pt2",

	"hdr_e8_sps0_tile_addr_lsb8",
	"hdr_f4_sps1_tile_addr_lsb8",

	"hdr_11c_curr_rvra_addr_lsb7",

	#"hdr_168_y_addr_lsb8",
	#"hdr_16c_uv_addr_lsb8",
	#"hdr_170_width_align",
	#"hdr_174_width_align",
	]
	s = ""
	for cand in cands:
		if (not isinstance(cand, str)):
			name, count = cand
			[name]
		else:
			name = cand
			count = None

		x0 = getattr(getattr(fp0, name[:3]), name)
		x1 = fp1[name]
		if isinstance(x0, ListContainer):
			num = len(x0) if not count else count
			for n in range(num):
				if (x0[n] == x1[n]): continue
				if (x1[n] != 0): # they fill out reference frames for IDR
					t = hl("%s[%d]: 0x%x 0x%x\n" % (name, n, x0[n], x1[n]), ANSI_RED)
					if not args.soft:
						print(t)
						assert(x0[n] == x1[n])
						continue
					s += t
		else:
			if (x0 == x1): continue
			if (x1 != 0): # they fill out reference frames for IDR
				t = hl("%s: 0x%x 0x%x\n" % (name, x0, x1), ANSI_RED)
				if not args.soft:
					print(t)
					assert(x0 == x1)
					continue
				s += t
	return s

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='Crappy unit test')
	parser.add_argument('-i', '--path', type=str, required=True, help="path to .h264")
	parser.add_argument('-d','--dir', type=str, required=True, help="matching .h264 trace dir")
	parser.add_argument('-p','--prefix', type=str, default="", help="dir prefix")
	parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
	parser.add_argument('-a', '--all', action='store_true', help="run all")
	parser.add_argument('-s', '--soft', action='store_true', help="don't assert")
	args = parser.parse_args()

	dec = AVDVP9Decoder()
	#dec.hal.stfu = True
	paths = os.listdir(os.path.join(args.prefix, args.dir))
	paths = sorted([os.path.join(args.prefix, args.dir, path) for path in paths if "param" in path or "frame" in path])

	num = len(paths) if args.all else args.num
	num = min(len(paths), num)
	slices = dec.setup(args.path, num, do_probs=0)
	for i in range(num):
		path = paths[i]
		fp0 = AVDVP9V3FrameParams.parse(open(path, "rb").read())
		sl = slices[i]
		print(sl)
		print(fp0)
		inst = dec.generate(sl)
		fp1 = dec.hal.fp
		#print(fp1)
		res = test(fp0, fp1, args)
		if (res):
			print(res)
		print()
