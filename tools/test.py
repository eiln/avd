#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import os

from avid.fp import *
from avid.utils import *
from avid.h264.decoder import AVDH264Decoder
from avid.h265.decoder import AVDH265Decoder
from avid.vp9.decoder import AVDVP9Decoder
from avd_emu import AVDEmulator

from tools.common import *

class AVDUnitTest:

	# I don't like any of the unit test frameworks
	# They can't even print simple asserts in hex

	def __init__(self, deccls, **kwargs):
		self.dec = deccls()
		self.dec.stfu = True
		self.dec.hal.stfu = True
		self.fp_keys = []
		self.pr_keys = []
		self.emu_ignore_keys = []
		self.args = dotdict(kwargs)
		if (self.args.debug_mode):
			self.dec.stfu = False

	def log(self, x, verbose=False):
		if ((not self.args.stfu) and ((not verbose) or (verbose and self.args.verbose))):
			print(f"[{hl('TST', ANSI_CYAN)}] {x}")

	def diff_fp_field(self, sl, x0, x1, name):
		if (x1 == 0): return # they fill out N/A fields
		if (x0 != x1) and (not (self.args.debug_mode)):
			print(sl)
		cassert(x0, x1, name)

	def diff_fp(self, sl, fp0, fp1, args):
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
					self.diff_fp_field(sl, x0[n], x1[n],  "%s[%d]" % (name, n))
			else:
				self.diff_fp_field(sl, x0, x1,  name)

	def get_paths(self, ident, args):
		paths = os.listdir(os.path.join(args.prefix, args.dir))
		paths = sorted([os.path.join(args.prefix, args.dir, path) for path in paths if ident in path])
		assert(len(paths))
		num = len(paths) if args.all else args.num
		num = min(len(paths), num)
		self.log(args)
		return paths, num

	def test_fp(self, args):
		self.log(hl("Testing fp '%s'..." % (args.dir), None))
		paths, num = self.get_paths("frame", args)
		slices = self.dec.setup(args.input, num=num, do_probs=0)
		count = 0
		for i in range(num):
			path = paths[i]
			if (self.args.show_paths):
				print(path)
			fp0 = self.dec.fpcls.parse(open(path, "rb").read())

			sl = slices[i]
			if (self.args.debug_mode) and (not self.args.show_headers):
				print(sl.show_slice_header().strip())
			if (self.args.show_headers):
				print(sl)
			if (self.args.show_fp):
				print(fp0)

			inst = self.dec.decode(sl)
			if (self.args.debug_mode):
				for x in inst:
					if (x.name in self.fp_keys):
						c = ANSI_GREEN
					elif ("cm3" in x.name):
						c = None
					else:
						c = ANSI_RED
					self.log(x.rep(clr=c))
			fp1 = self.dec.ffp
			res = self.diff_fp(sl, fp0, fp1, args)

			if (self.args.debug_mode):
				print()
			count += 1
		self.log(hl(f"Inst test '{args.dir}' ({count} frames) all good", ANSI_GREEN))

	def diff_emu(self, sl, inst0_stream, inst1_stream):
		l0, l1 = len(inst0_stream), len(inst1_stream)
		num = min(l0, l1)
		for n in range(num):
			x0 = inst0_stream[n]
			x1 = inst1_stream[n]
			if ((not self.args.show_all) and (x0 == x1.val)): continue
			if (not self.args.debug_mode and x1.name in self.emu_ignore_keys): continue

			s = ""
			if (self.args.show_index):
				s += f'[{hl(str(sl.idx).rjust(2), ANSI_CYAN)}]'
			s += f'[{hl(str(n).rjust(2), ANSI_GREEN)}] '

			if (self.args.show_bits):
				x0r = bitrepr32(x0)
				x1r = bitrepr32(x1.val)
				diff = f'{bitrepr_diff(x0r, x1r)} | {x1.get_disp_name()}'
				self.log(s + diff)
			else:
				x0r = f'{hex(x0).rjust(2+8)}'
				x1r = f'{hex(x1.val).rjust(2+8)}'
				if (x0 != x1.val):
					x0r = hl(x0r, ANSI_RED)
					x1r = hl(x1r, ANSI_RED)
				diff = f'{x0r} | {x1r} | {x1.get_disp_name()}'
				self.log(s + diff)
		if (l0 > l1):
			for n in range(l0 - l1):
				x0 = inst0_stream[n + l1]
				x1 = 0xdeadbeef

				s = ""
				if (self.args.show_index):
					s += f'[{hl(str(sl.idx).rjust(2), ANSI_CYAN)}]'
				s += f'[{hl(str(n + l1).rjust(2), ANSI_GREEN)}] '
				x0r = f'{hex(x0).rjust(2+8)}'
				x1r = f'{hex(x1).rjust(2+8)}'
				if (x0 != x1):
					x0r = hl(x0r, ANSI_RED)
					#x1r = hl(x1r, ANSI_RED)
				diff = f'{x0r} | {x1r} | '
				self.log(s + diff)

	def test_emu(self, args):
		self.dec.hal.stfu = True
		self.emu = AVDEmulator(args.firmware, stfu=True)
		self.emu.start()
		self.log(hl("Testing emu '%s'..." % (args.dir), None))
		paths, num = self.get_paths("frame", args)
		slices = self.dec.setup(args.input, num=num, do_probs=0)
		count = 0
		for i in range(num):
			path = paths[i]
			if (self.args.show_paths):
				print(path)
			assert(os.path.isfile(path))
			inst0_stream = self.emu.avd_cm3_cmd_decode(path)

			sl = slices[i]
			if (self.args.debug_mode) and (not self.args.show_headers):
				print(sl.show_slice_header().strip())
			if (self.args.show_headers):
				print(sl)

			inst1_stream = self.dec.decode(sl)
			self.diff_emu(sl, inst0_stream, inst1_stream)
			if (self.args.debug_mode):
				print()
			count += 1
		self.log(hl(f"Emu test '{args.dir}' ({count} frames) all good", ANSI_GREEN))

class AVDH264UnitTest(AVDUnitTest):
	def __init__(self, **kwargs):
		super().__init__(AVDH264Decoder, **kwargs)
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

			"hdr_9c_pps_tile_addr_lsb8",
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

			#"slc_76c_cmd_weights_denom",
			"slc_770_cmd_weights_weights",
			"slc_8f0_cmd_weights_offsets",
			"slc_a70_cmd_slice_qpy",
			"slc_a74_cmd_a3",
			"slc_a7c_cmd_d8",

			#"inp_8b4d4_slice_addr_low",
			#"inp_8b4d8_slice_hdr_size",
		]
		self.emu_ignore_keys = ["inp_8b4d4_slice_addr_low"]

class AVDH265UnitTest(AVDUnitTest):
	def __init__(self, **kwargs):
		super().__init__(AVDH265Decoder, **kwargs)
		self.name = hl("H265", ANSI_PURPLE)
		self.fp_keys = [
			"hdr_4c_cmd_start_hdr",
			"hdr_50_mode",
			"hdr_54_height_width",
			"hdr_58_pixfmt_zero",

			"hdr_28_height_width_shift3",
			"hdr_2c_sps_param",
			"hdr_30_flag_pt1",
			"hdr_34_flag_pt2",
			"hdr_5c_flag_pt3",
			"hdr_98_const_30",

			"hdr_1b4_y_addr_lsb8",
			"hdr_1b8_uv_addr_lsb8",
			"hdr_1bc_width_align",
			"hdr_1c0_width_align",

			"slc_bcc_cmd_slice_qp",
			"slc_bd0_cmd_flags",
			"slc_b08_cmd_weights_denom",
			"slc_b0c_cmd_weights_weights",
			"slc_b6c_cmd_weights_offsets",
			"slc_a8c_cmd_ref_type",
			#"slc_bd4_sps_tile_addr2_lsb8",
			"slc_be0_unk_100",
			"slc_bdc_slice_size",
		]

class AVDVP9UnitTest(AVDUnitTest):
	def __init__(self, **kwargs):
		super().__init__(AVDVP9Decoder, **kwargs)
		self.name = hl("VP9", ANSI_GREEN)
		self.fp_keys = [
			"hdr_28_height_width_shift3",
			"hdr_2c_txfm_mode",
			"hdr_30_cmd_start_hdr",
			"hdr_34_const_20",
			"hdr_38_height_width_shift3",
			"hdr_40_flags1_pt1",

			"hdr_e0_const_240",
			"hdr_104_probs_addr_lsb8",
			"hdr_118_pps0_tile_addr_lsb8",
			"hdr_108_pps1_tile_addr_lsb8",
			"hdr_110_pps2_tile_addr_lsb8",

			"hdr_4c_base_q_idx",
			"hdr_44_flags1_pt2",
			"hdr_48_loop_filter_level",

			"hdr_e8_sps0_tile_addr_lsb8",
			"hdr_f4_sps1_tile_addr_lsb8",

			"hdr_70_ref_height_width",
			"hdr_7c_ref_align",
			"hdr_9c_ref_100",
			#"hdr_11c_curr_rvra_addr_lsb7",
			#"hdr_138_ref_rvra0_addr_lsb7",
			#"hdr_144_ref_rvra1_addr_lsb7",
			#"hdr_150_ref_rvra2_addr_lsb7",
			#"hdr_15c_ref_rvra3_addr_lsb7",

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
		self.emu_ignore_keys = ["hdr_168_y_addr_lsb8", "hdr_16c_uv_addr_lsb8"]

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
		self.log(hl("Testing probs '%s'..." % (args.dir), None))
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
			if (self.args.show_paths):
				print(path)
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
			bassert(x0, x1)
			count += 1
		self.log(hl(f"Prob test '{args.dir}' ({count} frames) all good", ANSI_GREEN))

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='Unit test')
	parser.add_argument('-i', '--input', type=str, default="", help="path to bitstream")
	parser.add_argument('-d', '--dir', type=str, required=True, help="matching trace dir")
	parser.add_argument('-f', '--firmware', type=str, default="j293ap-13.5-viola-firmware.bin")
	parser.add_argument('-p', '--prefix', type=str, default="",  help="dir prefix")
	parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
	parser.add_argument('-a', '--all', action='store_true', help="run all")
	parser.add_argument('-v', '--verbose', action='store_true')
	parser.add_argument('-x', '--stfu', action='store_true')

	parser.add_argument('-j', '--test-fp', action='store_true')
	parser.add_argument('-e', '--test-emu', action='store_true')
	parser.add_argument('-q', '--test-probs', action='store_true')

	parser.add_argument('-u', '--debug-mode', action='store_true')
	parser.add_argument('-b', '--show-bits', action='store_true')
	parser.add_argument('--show-all', action='store_true')
	parser.add_argument('--show-headers', action='store_true')
	parser.add_argument('--show-index', action='store_true')
	parser.add_argument('--show-paths', action='store_true')
	parser.add_argument('--show-fp', action='store_true')

	args = parser.parse_args()
	args.firmware = resolve_input(args.firmware)
	args.dir = resolve_input(args.dir, isdir=True)
	args.input = resolve_input(args.dir)
	mode = ffprobe(args.dir)
	if  (mode == "h264"):
		ut = AVDH264UnitTest(**vars(args))
	elif (mode == "h265"):
		ut = AVDH265UnitTest(**vars(args))
	elif (mode == "vp09"):
		ut = AVDVP9UnitTest(**vars(args))
	else:
		raise ValueError("Codec %s not supported" % mode)

	if (args.test_fp):
		ut.test_fp(args)
	if (args.test_emu):
		ut.test_emu(args)
	if (args.test_probs):
		import numpy as np
		ut.test_probs(args)
