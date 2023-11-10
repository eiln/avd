#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..fp import *

class AVDV3VP9InstHeader(AVDFrameParams):
	subcon = "AvdH264V3InstHeader" / Struct(
		"hdr_28_height_width_shift3" / u32,
		"hdr_2c_sps_param" / ExprValidator(u32, obj_ & 0x1000000 == 0x1000000),
		"hdr_30_cmd_start_hdr" / ExprValidator(u32, obj_ & 0x2db00000 == 0x2db00000),
		"hdr_34_const_20" / ExprValidator(u32, obj_ == 0x2000000),
		"hdr_38_height_width_shift3" / u32,
		"hdr_3c_zero" / ExprValidator(u32, obj_ == 0x0),
		"hdr_40_flags_pt1" / u32,
		"hdr_44_flags_pt2" / u32,

		"hdr_48_incr_addr" / u32,
		"hdr_4c_incr_size" / u32,

		"hdr_50_scaling_list" / Array(8, u32),
		"hdr_70_ref_height_width" / Array(3, u32),
		"hdr_7c_ref_size" / Array(3, u32),
		"hdr_88" / u32,
		"hdr_8c" / u32,
		"hdr_90" / u32,
		"hdr_94_height_width" / u32,
		"hdr_98" / ExprValidator(u32, obj_ == 0x20000),
		"hdr_9c" / u32,
		"hdr_a0" / u32,
		"hdr_a4" / u32,
		"hdr_a8_inst_fifo_addr_lsb8" / Array(7, u32),
		"hdr_c4_inst_fifo_size" / Array(7, u32),

		"hdr_e0_pps2_tile_const_addr_lsb8" / u32, # 0x240
		"hdr_e4_zero" / ExprValidator(u32, obj_ == 0x0),

		"hdr_e8_sps0_tile_addr_lsb8" / ExprValidator(Array(3, u32), obj_[2] == 0x0),
		"hdr_f4_sps1_tile_addr_lsb8" / Array(4, u32),

		"hdr_104_probs_addr_lsb8" / u32,
		"hdr_108_pps1_tile_addr_lsb8" / Array(4, u32),
		"hdr_118_pps0_tile_addr_lsb8" / u32,

		"hdr_11c_curr_rvra_addr_lsb7" / Array(4, u32),
		"hdr_12c_pad" / ZPadding(12),
		"hdr_138_rvra0_addr_lsb7" / Array(3, u32),
		"hdr_144_rvra1_addr_lsb7" / Array(3, u32),
		"hdr_150_rvra2_addr_lsb7" / Array(3, u32),
		"hdr_15c_ef3_addr_lsb7" / Array(3, u32),

		"hdr_168_y_addr_lsb8" / u32,
		"hdr_16c_uv_addr_lsb8" / u32,
		"hdr_170_width_align" / u32,
		"hdr_174_width_align" / u32,

		"hdr_178_10001" / u32,
		"hdr_17c_10001" / u32,
		"etc"/ Array(32, u32),
	)
	def __init__(self):
		super().__init__()

class AVDVP9V3FrameParams(AVDFrameParams):
	subcon = Struct(
		"pio" / AVDV3PiodmaHeader,
		"hdr" / AVDV3VP9InstHeader,
	)
	def __init__(self):
		super().__init__()

	def __str__(self):
		return ''.join([str(getattr(self, x)) for x in ["hdr"]])

class AVDVP9V3FakeFrameParams(AVDFakeFrameParams):
	def __init__(self):
		super().__init__()
		self.keynames = ["hdr", "slc"]

	@classmethod
	def new(cls):
		obj = cls()
		obj["hdr_108_pps1_tile_addr_lsb8"] = [0] * 4
		obj["hdr_e8_sps0_tile_addr_lsb8"]  = [0] * 3
		obj["hdr_f4_sps1_tile_addr_lsb8"]  = [0] * 4
		obj["hdr_11c_curr_rvra_addr_lsb7"] = [0] * 4
		return obj
