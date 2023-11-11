#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..fp import *

class AVDVP9V3PiodmaHeader(AVDFrameParams):
	subcon = Struct(
		"pio_piodma1_word" / ExprValidator(u32, ((obj_ - 0x209ef15) % 4) == 0),
		"pio_4_codec" / ExprValidator(u32, obj_ == 2),
		"pio_8" / u32,
		"pio_c_piodma2_offset" / ExprValidator(u32, obj_ == 0x24aa4),
		"pio_10_notused" / u32,
		"pio_14_deadcafe" / ExprValidator(u32, obj_ == 0xdeadcafe),
		"pio_18_101_notused" / ExprValidator(u32, (obj_ & 0xfff) == 0x101),
		"pio_1c_slice_count" / ExprValidator(u32, obj_ == 0x0), # no slices for vp9
		"pio_20_piodma1_cmd" / ExprValidator(u32, obj_ == 0xaa4),
		"pio_24_pad" / ZPadding(0x4),
	)
	def __init__(self):
		super().__init__()

class AVDVP9V3InstHeader(AVDFrameParams):
	subcon = "AvdH264V3InstHeader" / Struct(
		"hdr_28_height_width_shift3" / u32,
		"hdr_2c_sps_param" / ExprValidator(u32, obj_ & 0x1000000 == 0x1000000),
		"hdr_30_cmd_start_hdr" / ExprValidator(u32, obj_ & 0x2db00000 == 0x2db00000),
		"hdr_34_const_20" / ExprValidator(u32, obj_ == 0x2000000),
		"hdr_38_height_width_shift3" / u32,
		"hdr_3c_zero" / ExprValidator(u32, obj_ == 0x0),

		"hdr_40_flags1_pt1" / u32,
		"hdr_44_flags1_pt2" / u32,
		"hdr_48_loop_filter_level" / u32,
		"hdr_4c_base_q_idx" / u32,

		"hdr_50_scaling_list" / Array(8, u32),
		"hdr_70_ref_height_width" / Array(3, u32),
		"hdr_7c_ref_align" / Array(3, u32),
		"hdr_88" / ExprValidator(u32, obj_ == 0x0),
		"hdr_8c" / ExprValidator(u32, obj_ == 0x0),
		"hdr_90" / ExprValidator(u32, obj_ == 0x0),
		"hdr_94_height_width" / u32,
		"hdr_98" / ExprValidator(u32, obj_ == 0x20000),
		"hdr_9c_ref_100" / Array(3, u32),
		"hdr_a8_inst_fifo_addr_lsb8" / Array(7, u32),
		"hdr_c4_inst_fifo_size" / Array(7, u32),

		"hdr_e0_const_240" / ExprValidator(u32, obj_ == 0x240),
		"hdr_e4_zero" / ExprValidator(u32, obj_ == 0x0),

		"hdr_e8_sps0_tile_addr_lsb8" / ExprValidator(Array(3, u32), obj_[2] == 0x0),
		"hdr_f4_sps1_tile_addr_lsb8" / Array(4, u32),

		"hdr_104_probs_addr_lsb8" / u32,
		"hdr_108_pps1_tile_addr_lsb8" / Array(4, u32),
		"hdr_118_pps0_tile_addr_lsb8" / u32,

		"hdr_11c_curr_rvra_addr_lsb7" / Array(4, u32),
		"hdr_12c_pad" / ZPadding(12),
		"hdr_138_ref_rvra0_addr_lsb7" / Array(3, u32),
		"hdr_144_ref_rvra1_addr_lsb7" / Array(3, u32),
		"hdr_150_ref_rvra2_addr_lsb7" / Array(3, u32),
		"hdr_15c_ref_rvra3_addr_lsb7" / Array(3, u32),

		"hdr_168_y_addr_lsb8" / u32,
		"hdr_16c_uv_addr_lsb8" / u32,
		"hdr_170_width_align" / u32,
		"hdr_174_width_align" / u32,
		"hdr_178" / Array(6, u32),
	)
	def __init__(self):
		super().__init__()

class AVDVP9V3DumbFuckingWasteOfMemory(AVDFrameParams):
	"""
	00000210: 00764099 00000000 00000000 00000000   .@v.............
	00000280: 00000000 00000000 00000000 00124111   .............A..
	000002a0: 00000000 0001f125 00000000 0001f125   ....%.......%...
	000002b0: 00000000 0001f125 00000000 0001f125   ....%.......%...
	00000aa0: 00000000 001df135 00000000 00000000   ....5...........
	00000ab0: 00040005 00000000 00920098 00000d86   ................
	00000ac0: 00000000 00070003 001df135 00000001   ........5.......
	00000ad0: 00010000 00040004 00000000 00920e22   ............"...
	00000ae0: 0000151f 00000004 00070007 001df135   ............5...
	00000af0: 00000002 00020000 00040004 00000000   ................
	00000b00: 00922345 0000171c 00000008 0007000b   E#..............
	00000b10: 001df135 00000003 00030000 00040004   5...............
	00000b20: 00000000 00923a61 00001701 0000000c   ....a:..........
	00000b30: 0007000f 00000000 00000000 00000000   ................
	00034ce0: 00000000 0025f569 00000000 00000000   ....i.%.........
	00034cf0: 010f0000 000e000f 04574024 0003753d   ........$@W.=u..

	You people ought to be ashamed of yourselves
	"""
	subcon = Struct(
		"dfw_190_pad" / ZPadding(0x70),
		"dfw_200" / Padding(0x10),
		"dfw_210_ipc" / ExprValidator(u32, obj_ == 0x764099),
		"dfw_214_ipc" / ZPadding(0x28c - 0x214),
		"dfw_28c_ipc" / ExprValidator(u32, obj_ == 0x124111),
		"dfw_290_pad" / ZPadding(0x10),
		"dfw_2a0_zero" / ExprValidator(u32, obj_ == 0x0),
	)
	def __init__(self):
		super().__init__()

class AVDVP9V3Tiles(AVDFrameParams):
	subcon = Struct(
		"til_2a4_0" / Array(2, u32),
		"til_2a4_1" / Array(2, u32),
		"til_2a4_2" / Array(2, u32),
		"til_2a4_3" / Array(2, u32),
		"til_2a4_4" / Array(2, u32),
		"til_2a4_5" / Array(2, u32),
		"til_2a4_6" / Array(2, u32),
		"til_2a4_7" / Array(2, u32),
		"til_2a4_pad" / Bytes(0x800 - 2 * 8 * 4),
		"til_aa4_pio_addr" / u32,
		"til_aa8_zero" / ExprValidator(u32, obj_ == 0x0),
		"til_aac_zero" / ExprValidator(u32, obj_ == 0x0),
		"til_ab0_40005" / ExprValidator(u32, obj_ == 0x40005),
		"til_ab4_zero" / ExprValidator(u32, obj_ == 0x0),
		"til_ab4_0" / Array(9, u32),
		"til_ab4_1" / Array(9, u32),
		"til_ab4_2" / Array(9, u32),
		"til_ab4_3" / Array(9, u32),
		"til_ab4_4" / Array(9, u32),
		"til_ab4_5" / Array(9, u32),
		"til_ab4_6" / Array(9, u32),
		"til_ab4_7" / Array(9, u32),
	)
	def __init__(self):
		super().__init__()

class AVDVP9V3FakeFrameParams(AVDFakeFrameParams):
	def __init__(self):
		super().__init__()
		self.keynames = ["hdr", "slc"]

	@classmethod
	def new(cls):
		obj = cls()
		obj["hdr_e8_sps0_tile_addr_lsb8"]  = [0] * 3
		obj["hdr_f4_sps1_tile_addr_lsb8"]  = [0] * 4
		obj["hdr_108_pps1_tile_addr_lsb8"] = [0] * 4
		obj["hdr_11c_curr_rvra_addr_lsb7"] = [0] * 4
		obj["hdr_138_ref_rvra0_addr_lsb7"]  = [0] * 3
		obj["hdr_144_ref_rvra1_addr_lsb7"]  = [0] * 3
		obj["hdr_150_ref_rvra2_addr_lsb7"]  = [0] * 3
		obj["hdr_15c_ref_rvra3_addr_lsb7"]  = [0] * 3
		obj["hdr_70_ref_height_width"] = [0] * 3
		obj["hdr_7c_ref_align"] = [0] * 3
		obj["hdr_9c_ref_100"] = [0] * 3
		return obj

class AVDVP9V3FrameParams(AVDFrameParams):
	subcon = Struct(
		"pio" / AVDVP9V3PiodmaHeader,
		"hdr" / AVDVP9V3InstHeader,
		"dfw" / AVDVP9V3DumbFuckingWasteOfMemory,
		"til" / AVDVP9V3Tiles,
	)
	_ffpcls = AVDVP9V3FakeFrameParams
	def __init__(self):
		super().__init__()

	def __str__(self):
		return ''.join([str(getattr(self, x)) for x in ["pio", "hdr", "til"]])
