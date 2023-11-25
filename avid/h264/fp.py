#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..fp import *

class AVDH264V3PiodmaHeader(AVDFrameParams):
	subcon = Struct(
		"pio_piodma1_word" / u32,
		"pio_4_codec" / ExprValidator(u32, obj_ >= 0 and obj_ <= 4), # 32 fucking bits for max 4 codes it doesn't need, this will be a recurring theme
		"pio_8_notused" / u32,
		"pio_c_notused" / u32,
		"pio_10_notused" / u32,
		"pio_14_deadcafe_notused" / ExprValidator(u32, obj_ == 0xdeadcafe),
		"pio_18_101_notused" / ExprValidator(u32, obj_ == 0x10101),
		"pio_1c_slice_count" / u32,
		"pio_20_piodma3_offset" / ExprValidator(u32, obj_ == 0x8b4c0),
		"pio_24_pad" / ZPadding(0x4),
	)
	def __init__(self):
		super().__init__()

class AVDH264V3InstHeader(AVDFrameParams):
	subcon = "AvdH264V3InstHeader" / Struct(
		"hdr_28_height_width_shift3" / u32,
		"hdr_2c_sps_param" / u32,
		"hdr_30_zero" / ExprValidator(u32, obj_ == 0),
		"hdr_34_cmd_start_hdr" / ExprValidator(u32, obj_ & 0x2db00000 == 0x2db00000),
		"hdr_38_mode" / u32,
		"hdr_3c_height_width" / u32,
		"hdr_40_zero" / ExprValidator(u32, obj_ == 0),
		"hdr_44_is_idr_mask" / u32,
		"hdr_48_3de" / u32,
		"hdr_4c_zero" / ExprValidator(u32, obj_ == 0),
		"hdr_50_zero" / ExprValidator(u32, obj_ == 0),
		"hdr_54_height_width" / u32,
		"hdr_58_const_3a" / ExprValidator(u32, obj_ == 0x30000a),

		"hdr_5c_inst_fifo_addr_lsb8" / Array(7, u32),
		"hdr_78_inst_fifo_conf_lsb8" / Array(7, u32),
		"hdr_94_pad" / ZPadding(0x8),

		"hdr_9c_pps_tile_addr_lsb8" / Array(8, u32),
		"hdr_bc_sps_tile_addr_lsb8" / u32,

		"hdr_c0_curr_ref_addr_lsb7" / Array(4, u32),
		"hdr_d0_ref_hdr" / Array(16, u32),
		"hdr_110_ref0_addr_lsb7" / Array(16, u32),
		"hdr_150_ref1_addr_lsb7" / Array(16, u32),
		"hdr_190_ref2_addr_lsb7" / Array(16, u32),
		"hdr_1d0_ref3_addr_lsb7" / Array(16, u32),

		"hdr_210_y_addr_lsb8" / u32,
		"hdr_214_uv_addr_lsb8" / u32,
		"hdr_218_width_align" / u32,
		"hdr_21c_width_align" / u32,
	)
	def __init__(self):
		super().__init__()

class AVDH264V3DumbFuckingWasteOfMemory(AVDFrameParams):
	subcon = Struct(
		"dfw_220_pad" / ZPadding(0x60),
		"dfw_280_chunk0" / Bytes(0x1e4),
		"dfw_464_chunk1" / Bytes(0x1e4),
		"dfw_648_chunk2" / Bytes(0x88),
		"dfw_6d0_pad" / ZPadding(0x10),
	)
	def __init__(self):
		super().__init__()

class AVDH264V3Slice(AVDFrameParams):
	subcon = Struct(
		"slc_6e0_piodma2_word" / u32,
		"slc_6e4_cmd_ref_type" / u32,
		"slc_6e8_cmd_ref_list_0" / Array(16, u32),
		"slc_728_cmd_ref_list_1" / Array(16, u32),
		"slc_768_unk" / u32,
		"slc_76c_cmd_weights_denom" / u32,
		"slc_770_cmd_weights_weights" / Array(96, u32),
		"slc_8f0_cmd_weights_offsets" / Array(96, u32),
		"slc_a70_cmd_slice_qpy" / u32,
		"slc_a74_cmd_flags" / u32,
		"slc_a78_sps_tile_addr2_lsb8" / u32,
		"slc_a7c_cmd_d8" / u32,
		"slc_a80_slice_addr_high_notused" / ExprValidator(u32, obj_ == 0),
		"slc_a84_slice_addr_low_notused" / u32,
		"slc_a88_slice_hdr_size_notused" / u32,
		"slc_a8c_pad" / ZPadding(0x8),
	)
	def __init__(self):
		super().__init__()

class AVDH264V3Input(AVDFrameParams):
	subcon = Struct(
		"inp_8b4c0_piodma1_word" / u32,
		"inp_8b4c4_zero" / ExprValidator(u32, obj_ == 0),
		"inp_8b4c8_zero" / ExprValidator(u32, obj_ == 0),
		"inp_8b4cc_f0000_notused" / u32,
		"inp_8b4d0_slice_addr_high" / ExprValidator(u32, obj_ == 0),
		"inp_8b4d4_slice_addr_low" / u32,
		"inp_8b4d8_slice_hdr_size" / u32,
		"inp_8b4dc_pad" / ZPadding(0x4),
	)
	def __init__(self):
		super().__init__()

class AVDH264V3FakeFrameParams(AVDFakeFrameParams):
	def __init__(self):
		super().__init__()
		self.keynames = ["hdr", "slc", "inp"]

	@classmethod
	def new(cls):
		obj = cls()
		obj["hdr_5c_inst_fifo_addr_lsb8"] = [0] * 7
		obj["hdr_78_inst_fifo_conf_lsb8"] = [0] * 7

		obj["hdr_9c_pps_tile_addr_lsb8"] = [0] * 8
		obj["hdr_c0_curr_ref_addr_lsb7"] = [0] * 4
		obj["hdr_d0_ref_hdr"] = [0] * 16
		obj["hdr_bc_sps_tile_addr_lsb8"] = 0

		obj["hdr_110_ref0_addr_lsb7"] = [0] * 16
		obj["hdr_150_ref1_addr_lsb7"] = [0] * 16
		obj["hdr_190_ref2_addr_lsb7"] = [0] * 16
		obj["hdr_1d0_ref3_addr_lsb7"] = [0] * 16

		obj["slc_6e8_cmd_ref_list_0"] = [0] * 16
		obj["slc_728_cmd_ref_list_1"] = [0] * 16
		obj["slc_770_cmd_weights_weights"] = [0] * 96
		obj["slc_8f0_cmd_weights_offsets"] = [0] * 96
		return obj

class AVDH264V3FrameParams(AVDFrameParams):
	subcon = Struct(
		"pio" / AVDH264V3PiodmaHeader,
		"hdr" / AVDH264V3InstHeader,
		"dfw" / AVDH264V3DumbFuckingWasteOfMemory,
		"slc" / AVDH264V3Slice,
		#"slc2" / Array(599, AvdH264V3Slice), # comment out for greatly faster construct parsing time
		#"inp" / AvdH264V3Input,
	)
	_ffpcls = AVDH264V3FakeFrameParams
	def __init__(self):
		super().__init__()

	def __str__(self):
		return ''.join([str(getattr(self, x)) for x in ["pio", "hdr", "slc"]])
