#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..fp import *

class AVDH265V3PiodmaHeader(AVDFrameParams):
	subcon = Struct(
		"pio_piodma1_word" / ExprValidator(u32, ((obj_ - 0x221ef15) % 4) == 0),
		"pio_4_codec" / ExprValidator(u32, obj_ == 0),
		"pio_8" / u32,
		"pio_c_zero" / ExprValidator(u32, obj_ == 0x0),
		"pio_10_notused" / u32,
		"pio_14_deadcafe" / ExprValidator(u32, obj_ == 0xdeadcafe),
		"pio_18_101_notused" / ExprValidator(u32, (obj_ & 0xfff) == 0x101),
		"pio_1c_slice_count" / u32,
		"pio_20_piodma2_cmd" / ExprValidator(u32, obj_ == 0x34ce4),
		"pio_24_piodma3_cmd" / ExprValidator(u32, obj_ == 0x4ace4),
	)
	def __init__(self):
		super().__init__()

class AVDH265V3InstHeader(AVDFrameParams):
	subcon = Struct(
		"hdr_28_height_width_shift3" / u32,
		"hdr_2c_sps_param" / u32,
		"hdr_30_flag_pt1" / ExprValidator(u32, obj_ == 0),
		"hdr_34_flag_pt2" / ExprValidator(u32, obj_ == 0x208),
		"hdr_38_zero" / ExprValidator(u32, obj_ == 0),
		"hdr_3c_zero" / ExprValidator(u32, obj_ == 0),
		"hdr_40_zero" / ExprValidator(u32, obj_ == 0),
		"hdr_44_zero" / ExprValidator(u32, obj_ == 0),
		"hdr_48_zero" / ExprValidator(u32, obj_ == 0),

		"hdr_4c_cmd_start_hdr" / ExprValidator(u32, obj_ & 0x2db00000 == 0x2db00000),
		"hdr_50_mode" / ExprValidator(u32, obj_ == 0),
		"hdr_54_height_width" / u32,
		"hdr_58_pixfmt_zero" / ExprValidator(u32, obj_ == 0),
		"hdr_5c_flag_pt3" / u32,
		"hdr_60_pad" / ZPadding(0x30),
		"hdr_90_zero" / ExprValidator(u32, obj_ == 0),
		"hdr_94_height_width" / u32,
		"hdr_98_const_30" / ExprValidator(u32, obj_ == 0x300000),
		"hdr_ac_inst_fifo_addr_lsb8" / Array(7, u32),
		"hdr_b8_inst_fifo_conf_lsb8" / Array(7, u32),
		"hdr_c4_pad" / ZPadding(0x8),

		"hdr_dc_pps_tile_addr_lsb8" / Array(10, u32),
		"hdr_104_curr_ref_addr_lsb7" / Array(4, u32),
		"hdr_114_ref_hdr" / Array(8, u32),
		"hdr_134_ref0_addr_lsb7" / Array(8, u32),
		"hdr_154_ref1_addr_lsb7" / Array(8, u32),
		"hdr_174_ref2_addr_lsb7" / Array(8, u32),
		"hdr_194_ref3_addr_lsb7" / Array(8, u32),

		"hdr_1b4_y_addr_lsb8" / u32,
		"hdr_1b8_uv_addr_lsb8" / u32,
		"hdr_1bc_width_align" / u32,
		"hdr_1c0_width_align" / u32,
		"hdr_1c4_pad" / Padding(0x3c),
	)
	def __init__(self):
		super().__init__()

class AVDH265V3DumbFuckingWasteOfMemory(AVDFrameParams):
	"""
	000001c0: 00000008 00010001 00020000 00000000   ................
	000001f0: 00000000 00000001 00000000 00000000   ................
	00000220: 00000000 00000000 03de28b5 00000000   .........(......
	00000600: 00000000 00000000 00000000 03de28b5   .............(..
	000009f0: 00764099 00000000 00000000 00000000   .@v.............
	00000a60: 00000000 00000000 00000000 00124111   .............A..
	00000a80: 00000000 015e0e0d 2d049056 2dc00000   ......^.V..-...-
	00000a90: 2dc00011 2dc00022 2dc00103 00000000   ...-"..-...-....
	00000b00: 00000000 00000000 2dd00000 00000000   ...........-....
	00000bc0: 00000000 00000000 00000000 2d905c00   .............\.-
	00000bd0: 2da500c0 000076c0 0074400d 00000117   ...-.v...@t.....
	00000be0: 01000000 00000000 00000000 00000000   ................
	00034ce0: 00000000 00261239 00000000 00000000   ....9.&.........
	00034cf0: 010f0000 000e000f 0074400d 00000117   .........@t.....
	"""
	subcon = Struct(
		"dfw_200_pad" / ZPadding(0x20),
		"dfw_200_pad" / ZPadding(0x8),
		"dfw_228_ipc" / ExprValidator(u32, obj_ == 0x3de28b5),
		"dfw_22c_ipc" / ZPadding(0x60c - 0x22c),
		"dfw_60c_ipc" / ExprValidator(u32, obj_ == 0x3de28b5),
		"dfw_610_pad" / ZPadding(0x9f0 - 0x610),
		"dfw_9f0_ipc" / ExprValidator(u32, obj_ == 0x764099),
		"dfw_9f4_ipc" / ZPadding(0xa6c - 0x9f4),
		"dfw_a6c_ipc" / ExprValidator(u32, obj_ == 0x124111),
		"dfw_a70_pad" / ZPadding(0xa84 - 0xa70),
	)
	def __init__(self):
		super().__init__()

class AVDH265V3Slice(AVDFrameParams):
	subcon = Struct(
		"slc_a88_unk" / u32,
		"slc_a8c_cmd_ref_type" / u32,
		"slc_a90_cmd_ref_list" / Array(30, u32),
		"slc_b04_unk_count" / u32,
		"slc_b08_cmd_weights_denom" / ExprValidator(u32, obj_ & 0x2dd00000 == 0x2dd00000),
		"slc_b0c_cmd_weights_weights" / Array(24, u32),
		"slc_b6c_cmd_weights_offsets" / Array(24, u32),
		"slc_bcc_cmd_slice_qp" / ExprValidator(u32, obj_ & 0x2d900000 == 0x2d900000),
		"slc_bd0_cmd_flags" / ExprValidator(u32, obj_ & 0x2da00000 == 0x2da00000),
		"slc_bd4_sps_tile_addr2_lsb8" / u32,
		"slc_bd8_slice_addr" / u32,
		"slc_bdc_slice_size" / u32,
		"slc_be0_unk_100" / ExprValidator(u32, obj_ == 0x1000000),
	)
	def __init__(self):
		super().__init__()

class AVDH265V3FakeFrameParams(AVDFakeFrameParams):
	def __init__(self):
		super().__init__()

	@classmethod
	def new(cls):
		obj = cls()
		obj["hdr_ac_inst_fifo_addr_lsb8"] = [0] * 7
		obj["hdr_b8_inst_fifo_conf_lsb8"] = [0] * 7

		obj["hdr_104_curr_ref_addr_lsb7"] = [0] * 4
		obj["hdr_114_ref_hdr"] = [0] * 8

		obj["hdr_134_ref0_addr_lsb7"] = [0] * 8
		obj["hdr_154_ref1_addr_lsb7"] = [0] * 8
		obj["hdr_174_ref2_addr_lsb7"] = [0] * 8
		obj["hdr_194_ref3_addr_lsb7"] = [0] * 8

		obj["slc_a90_cmd_ref_list"] = [0] * 30
		obj["slc_b08_cmd_weights_denom"] = 0
		obj["slc_b0c_cmd_weights_weights"] = [0] * 96
		obj["slc_b6c_cmd_weights_offsets"] = [0] * 96

		obj["slc_bd4_sps_tile_addr2_lsb8"] = 0
		obj["hdr_9c_pps_tile_addr_lsb8"] = [0] * 8
		obj["hdr_bc_sps_tile_addr_lsb8"] = 0
		return obj

class AVDH265V3FrameParams(AVDFrameParams):
	subcon = Struct(
		"pio" / AVDH265V3PiodmaHeader,
		"hdr" / AVDH265V3InstHeader,
		"dfw" / AVDH265V3DumbFuckingWasteOfMemory,
		"slc" / AVDH265V3Slice,
	)
	_ffpcls = AVDH265V3FakeFrameParams
	def __init__(self):
		super().__init__()

	def __str__(self):
		return ''.join([str(getattr(self, x)) for x in ["hdr", "slc"]])
