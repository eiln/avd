#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import os
from termcolor import colored

from avid.h264.decoder import AVDH264Decoder
from avid.h264.fp import *
from avid.utils import *

def test(fp0, fp1, args):
	cands = [
	"hdr_28_height_width_shift3",
	"hdr_2c_sps_param",
	"hdr_34_cmd_start_hdr",
	"hdr_38_pixfmt",
	"hdr_3c_height_width",
	"hdr_44_is_idr_mask",
	"hdr_48_3de",
	"hdr_54_height_width",
	"hdr_58_const_3a",

	("hdr_9c_pps_tile_addr_lsb8", 4),
	"hdr_bc_sps_tile_addr_lsb8",

	"hdr_c0_curr_ref_addr_lsb7",
	"hdr_d0_ref_hdr",
	"hdr_110_ref0_addr_lsb7",
	"hdr_150_ref1_addr_lsb7",
	"hdr_190_ref2_addr_lsb7",
	"hdr_1d0_ref3_addr_lsb7",

	"hdr_210_y_addr_lsb8",
	"hdr_214_uv_addr_lsb8",
	"hdr_218_width_align",
	"hdr_21c_width_align",

	"slc_6e4_cmd_ref_type",
	"slc_6e8_cmd_ref_list_0",
	"slc_728_cmd_ref_list_1",
	"slc_770_cmd_weights_weights",
	"slc_8f0_cmd_weights_offsets",
	"slc_a70_cmd_slice_qpy",
	"slc_a74_cmd_a3",
	"slc_a7c_cmd_d8",

	#"inp_8b4d4_slice_addr_low",
	#"inp_8b4d8_slice_hdr_size",
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

	dec = AVDH264Decoder()
	dec.hal.stfu = True
	slices = dec.setup(args.path)
	paths = os.listdir(os.path.join(args.prefix, args.dir))
	paths = sorted([os.path.join(args.prefix, args.dir, path) for path in paths if "param" in path or "frame" in path])
	paths = paths if args.all else paths[:args.num]
	for i,path in enumerate(paths):
		#print(path)
		fp0 = AVDH264V3FrameParams.parse(open(path, "rb").read())
		sl = slices[i]
		print(sl)
		inst = dec.generate(sl)
		fp1 = dec.hal.fp
		#print(fp0)
		#print(fp1)
		res = test(fp0, fp1, args)
		if (res):
			print(res)
		print()
