#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import os

from avid.fp import *
from avid.utils import *
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
		cassert(x0, x1, name, fatal=not self.args.non_fatal)

	def diff_fp(self, sl, fp0, fp1, args):
		for cand in self.fp_keys:
			if (not isinstance(cand, str)):
				name, count = cand
			else:
				name, count = cand, None
			x0 = getattr(getattr(fp0, name[:3]), name)
			if (not (hasattr(fp1, name))):
				if (isinstance(x0, ListContainer)):
					x1 = [0] * len(x0)
				else:
					x1 = 0
			else:
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

	def init_hook(self):
		if (self.args.debug_mode and self.args.show_headers):
			if (self.dec.mode in ["h264", "h265"]):
				for x in self.dec.ctx.sps_list:
					if (x):
						print(x)
				if (self.dec.mode in ["h264"]):
					for x in self.dec.ctx.pps_list:
						if (x):
							print(x)

	def show_mini_header(self, sl):
		if (self.args.debug_mode) and (not self.args.show_headers):
			print(sl.show_slice_header().strip())
			if hasattr(sl, "slices"):
				for s in sl.slices:
					print(s.show_slice_header().strip())

	def test_fp(self, args):
		self.log(hl("Testing fp '%s'..." % (args.dir), None))
		paths, num = self.get_paths("frame", args)
		slices = self.dec.setup(args.input, **vars(args))
		self.init_hook()
		count = 0
		for i in range(num):
			path = paths[i]
			if (self.args.show_paths):
				print(path)
			fp0 = self.dec.fpcls.parse(open(path, "rb").read())

			sl = slices[i]
			self.show_mini_header(sl)
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

			if (x0 != x1.val):
				c = ANSI_RED
			else:
				c = ANSI_GREEN
			s += f'[{hl(str(n).rjust(3), c)}] '

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
				s += f'[{hl(str(n + l1).rjust(3), ANSI_RED)}] '
				x0r = f'{hex(x0).rjust(2+8)}'
				x1r = f'{hex(x1).rjust(2+8)}'
				if (x0 != x1):
					x0r = hl(x0r, ANSI_RED)
					#x1r = hl(x1r, ANSI_RED)
				diff = f'{x0r} | {x1r} | '
				self.log(s + diff)

	def test_emu(self, args):
		from avd_emu import AVDEmulator
		self.dec.hal.stfu = True
		self.emu = AVDEmulator(args.firmware, stfu=True)
		self.emu.start()
		self.log(hl("Testing emu '%s'..." % (args.dir), None))
		paths, num = self.get_paths("frame", args)
		slices = self.dec.setup(args.input, do_probs=0, **vars(args))
		self.init_hook()
		count = 0
		for i in range(num):
			path = paths[i]
			if (self.args.show_paths):
				print(path)
			assert(os.path.isfile(path))
			inst0_stream = self.emu.avd_cm3_cmd_decode(path)

			sl = slices[i]
			self.show_mini_header(sl)
			if (self.args.show_headers):
				print(sl)

			inst1_stream = self.dec.decode(sl)
			self.diff_emu(sl, inst0_stream, inst1_stream)
			if (self.args.debug_mode):
				print()
			count += 1
		self.log(hl(f"Emu test '{args.dir}' ({count} frames) all good", ANSI_GREEN))

class AVDH264UnitTest(AVDUnitTest):
	def __init__(self, dec, **kwargs):
		super().__init__(dec, **kwargs)
		self.name = hl("H264", ANSI_BLUE)
		self.fp_keys = [
			"hdr_28_height_width_shift3",
			"hdr_2c_sps_param",
			"hdr_30_seq_scaling_list_dims",
			"hdr_34_cmd_start_hdr",
			"hdr_38_mode",
			"hdr_3c_height_width",
			"hdr_40_zero",
			"hdr_44_flags",
			"hdr_48_chroma_qp_index_offset",
			"hdr_4c_pic_scaling_list_dims",
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

			"scl_28c_seq_scaling_matrix_4x4",
			"scl_2ec_seq_scaling_matrix_8x8",
			"scl_46c_pic_scaling_matrix_4x4",
			"scl_4cc_pic_scaling_matrix_8x8",

			"slc_6e4_cmd_ref_type",
			"slc_6e8_cmd_ref_list_0",
			"slc_728_cmd_ref_list_1",

			"slc_76c_cmd_weights_denom",
			"slc_770_cmd_weights_weights",
			"slc_8f0_cmd_weights_offsets",
			"slc_a70_cmd_quant_param",
			"slc_a74_cmd_deblocking_filter",
			"slc_a7c_cmd_set_coded_slice",
			"slc_a78_sps_tile_addr2_lsb8",
		]
		self.emu_ignore_keys = ["slc_a84_slice_addr_low"]

class AVDH265UnitTest(AVDUnitTest):
	def __init__(self, dec, **kwargs):
		super().__init__(dec, **kwargs)
		self.name = hl("H265", ANSI_PURPLE)
		self.fp_keys = [
			"hdr_4c_cmd_start_hdr",
			"hdr_50_mode",
			"hdr_54_height_width",
			"hdr_58_pixfmt_zero",

			"hdr_28_height_width_shift3",
			"hdr_2c_sps_txfm",
			"hdr_30_sps_pcm",
			"hdr_34_sps_flags",
			"hdr_5c_pps_flags",
			"hdr_60_pps_qp",
			"hdr_64_zero",
			"hdr_68_zero",
			"hdr_6c_zero",
			"hdr_70_zero",
			"hdr_74_zero",
			"hdr_78_zero",
			"hdr_98_const_30",

			"hdr_38_sps_scl_dims",
			"hdr_3c_sps_scl_dims",
			"hdr_40_sps_scl_dims",
			"hdr_44_sps_scl_dims",
			"hdr_48_sps_scl_dims",

			"scl_22c_seq_scaling_matrix_4x4",
			"scl_28c_seq_scaling_matrix_8x8",
			"scl_40c_seq_scaling_matrix_16x16",
			"scl_58c_seq_scaling_matrix_32x32",

			"hdr_dc_pps_tile_addr_lsb8",
			#"hdr_104_curr_ref_addr_lsb7",
			"hdr_114_ref_hdr",
			#"slc_bd4_sps_tile_addr2_lsb8",

			"hdr_1b4_y_addr_lsb8",
			"hdr_1b8_uv_addr_lsb8",
			"hdr_1bc_width_align",
			"hdr_1c0_width_align",

			"slc_bcc_cmd_quantization",
			"slc_bd0_cmd_deblocking_filter",
			"slc_b08_cmd_weights_denom",
			"slc_b0c_cmd_weights_weights",
			"slc_b6c_cmd_weights_offsets",
			"slc_a8c_cmd_ref_type",
			"slc_a90_cmd_ref_list",
			#"slc_be0_unk_100",
			#"slc_bdc_slice_size",
		]

class AVDVP9UnitTest(AVDUnitTest):
	def __init__(self, dec, **kwargs):
		super().__init__(dec, **kwargs)
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

def test(args):
	if ((not args.list_data) and (args.list_data) or (args.mode and not (args.dir or args.input))):
		args.list_data = [args.mode]
	if (args.list_data) or (args.mode and not (args.dir or args.input)):
		for x in args.list_data:
			print(f"codec: {x}")
			dname = resolve_input(x, isdir=True)
			print(dname)
			paths = [d for d in os.listdir(dname) if os.path.isdir(os.path.join(dname, d))]
			for p in sorted(paths):
				print(f"\t{p}")
			print()
		return

	args.dir = resolve_input(args.dir, isdir=True, mode=args.mode)
	args.input = resolve_input(args.dir)
	if (not (args.test_fp or args.test_emu or args.test_probs)):
		if (args.show_headers):
			from tools.hdr import print_headers
			headers = print_headers(args.input, args.num)
			for x in headers[:args.num]:
				print(x)
		return

	if (not args.mode):
		args.mode = ffprobe(args.dir)

	if (args.show_all):
		args.debug_mode = 1

	if  (args.mode == "h264"):
		from avid.h264.decoder import AVDH264Decoder
		ut = AVDH264UnitTest(AVDH264Decoder, **vars(args))
	elif (args.mode == "h265"):
		from avid.h265.decoder import AVDH265Decoder
		ut = AVDH265UnitTest(AVDH265Decoder, **vars(args))
	elif (args.mode == "vp09"):
		from avid.vp9.decoder import AVDVP9Decoder
		ut = AVDVP9UnitTest(AVDVP9Decoder, **vars(args))
	else:
		raise ValueError("Codec %s not supported" % args.mode)

	if (args.test_fp):
		ut.test_fp(args)
	if (args.test_emu):
		args.firmware = resolve_input(args.firmware)
		ut.test_emu(args)
	if (args.test_probs):
		import numpy as np
		ut.test_probs(args)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='Unit test')
	parser.add_argument('-m', '--mode', type=str, default="", help="codec mode")
	parser.add_argument('-i', '--input', type=str, default="", help="path to bitstream")
	parser.add_argument('-d', '--dir', type=str, default="", help="matching trace dir")
	parser.add_argument('-l','--list-data', nargs='+', type=str, help="list test data for codecs")

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
	parser.add_argument('-nf', '--non-fatal', action='store_true')
	parser.add_argument('-ns', '--nal-stop', action='store_true')

	parser.add_argument('-sa', '--show-all', action='store_true')
	parser.add_argument('-sh', '--show-headers', action='store_true')
	parser.add_argument('-si', '--show-index', action='store_true')
	parser.add_argument('-sp', '--show-paths', action='store_true')
	parser.add_argument('-sf', '--show-fp', action='store_true')

	args = parser.parse_args()
	test(args)
