#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import os
import numpy as np

from avid.fp import *
from avid.utils import *
from avid.h264.decoder import AVDH264Decoder
from avid.vp9.decoder import AVDVP9Decoder
from tools.common import *

class AVDUnitTest:

	# I don't like any of the unit test frameworks
	# They can't even print simple asserts in hex

	def __init__(self, deccls, stfu=False, verbose=False):
		self.dec = deccls()
		self.dec.stfu = True
		self.dec.hal.stfu = True
		self.fp_keys = []
		self.pr_keys = []
		#self.emu = AVDEmulator()
		self.stfu = stfu
		self.verbose = verbose

	def log(self, x, verbose=False):
		if ((not self.stfu) and ((not verbose) or (verbose and self.verbose))):
			print(f"[TEST][{self.name}] {x}")

	def diff_fp(self, fp0, fp1, args):
		for cand in self.fp_keys:
			if (not isinstance(cand, str)):
				name, count = cand
			else:
				name, count = cand, None
			x0 = getattr(getattr(fp0, name[:3]), name)
			x1 = fp1[name]
			if (isinstance(x0, ListContainer)):
				num = len(x0) if not count else count
				for n in range(num):
					if (x1[n] == 0): continue  # they fill out N/A fields
					cassert(x0[n], x1[n], "%s[%d]" % (name, n))
			else:
				if (x1 == 0): continue
				cassert(x0, x1, name)

	def get_paths(self, ident, args):
		paths = os.listdir(os.path.join(args.prefix, args.dir))
		paths = sorted([os.path.join(args.prefix, args.dir, path) for path in paths if ident in path])
		assert(len(paths))
		num = len(paths) if args.all else args.num
		num = min(len(paths), num)
		self.log(args)
		return paths, num

	def test_inst(self, args):
		self.log(hl("Testing inst '%s...'" % (args.dir), None))
		paths, num = self.get_paths("frame", args)
		slices = self.dec.setup(args.input, num=num, do_probs=0)
		count = 0
		for i in range(num):
			path = paths[i]
			self.log("%03d: %s" % (count, path), verbose=True)
			sl = slices[i]
			inst = self.dec.decode(sl)
			assert(os.path.isfile(path))
			fp0 = self.dec.fpcls.parse(open(path, "rb").read())
			fp1 = self.dec.ffp
			res = self.diff_fp(fp0, fp1, args)
			count += 1
		self.log(hl(f"Inst test '{args.dir}' ({count} frames) all good", ANSI_GREEN))

class AVDH264UnitTest(AVDUnitTest):
	def __init__(self):
		super().__init__(AVDH264Decoder)
		self.name = hl("H264", ANSI_BLUE)
		self.fp_keys = [
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

class AVDVP9UnitTest(AVDUnitTest):
	def __init__(self):
		super().__init__(AVDVP9Decoder)
		self.name = hl("VP9", ANSI_GREEN)
		self.fp_keys = [
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
		self.pr_keys = ["tx8p", "tx16p", "tx32p", "coef",
				"skip", "inter_mode", "switchable_interp",
				"intra_inter", "comp_inter", "single_ref",
				"comp_ref", "y_mode", "uv_mode", "partition",
				"mv_joint"]

	def diff_prob_field(self, sl, a, b, key):
		if (not np.array_equal(a, b)):
			header = "[slice: %d] " % sl.idx
			self.log(hl(header + "=" * 40))
			self.log(key)
			#print(a)
			#print(b)
			#print(np.column_stack((a, b)))
			diff = a - b
			print(diff)
			self.log(hl("=" * (len(header) + 40)))
		return not np.array_equal(a, b)

	def test_probs(self, args):
		assert(self.dec.probscls)
		self.log(hl("Testing probs %s..." % (args.dir), None))
		paths, num = self.get_paths("probs", args)
		slices = self.dec.setup(args.input, num=num, do_probs=1)

		ret = 0
		count = 0
		for i in range(num):
			#pidx = i * 4 + (i % 4)
			pidx = i
			if (pidx > len(paths)):
				break
			path = paths[pidx]
			self.log("%03d: %s" % (count, path), verbose=True)
			assert(os.path.isfile(path))
			x0 = open(paths[pidx], "rb").read()[:self.dec.probscls.sizeof()]
			prx0 = self.dec.probscls.parse(x0)

			sl = slices[i]
			prx1 = sl.probs
			x1 = sl.probs.to_avdprobs(prx1)
			for key in self.pr_keys:
				a = prx0[key]
				b = prx1[key]
				ret |= self.diff_prob_field(sl, a, b, key)
				for j in range(2): # eh
					for key in ["sign", "classes", "class0", "bits", "class0_fp", "fp", "class0_hp", "hp"]:
						a = prx0["mv_comp"][j][key]
						b = prx1["mv_comp"][j][key]
						ret |= self.diff_prob_field(sl, a, b, key)
			if (ret):
				print(sl)
			bassert(x0, x1, nonfatal=False)
			count += 1
		self.log(hl(f"Prob test '{args.dir}' ({count} frames) all good", ANSI_GREEN))
