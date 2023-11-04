#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..fp import *

class AvdV3VP9InstHeader(ConstructClass):
	subcon = "AvdH264V3InstHeader" / Struct(
		"hdr_28_height_width_shift3" / u32,
		"hdr_2c_sps_param" / u32,
		"hdr_30_cmd_start_hdr" / ExprValidator(u32, obj_ & 0x2db00000 == 0x2db00000),
		"hdr_34_const_20" / ExprValidator(u32, obj_ == 0x2000000),
		"hdr_38_height_width" / u32,
		"hdr_3c_zero" / ExprValidator(u32, obj_ == 0),
		"hdr_40_flags" / u32,
		"hdr_44_flags_pt2" / u32,

		"hdr_48_incr_addr" / u32,
		"hdr_4c_incr_size" / u32,

		"hdr_50" / Array(8, u32),
		"hdr_70_ref_height_width" / Array(3, u32),
		"hdr_7c_ref_size" / Array(3, u32),
		"hdr_88" / u32,
		"hdr_8c" / u32,
		"hdr_90" / Array(4, u32),
		"hdr_a0" / Array(16, u32),
		"hdr_e0_240_addr_lsb8" / u32,
		"hdr_e4" / u32,
		"hdr_e8_addr_lsb8" / Array(13, u32),
		"hdr_11c_addr_lsb8" / Array(4, u32),
		"hdr_12c_pad" / Array(3, u32),
		"hdr_138_ef0_addr_lsb8" / Array(3, u32),
		"hdr_144_ef1_addr_lsb8" / Array(3, u32),
		"hdr_150_ef2_addr_lsb8" / Array(3, u32),
		"hdr_15c_ef3_addr_lsb8" / Array(3, u32),

		"hdr_168_y_addr_lsb8" / u32,
		"hdr_16c_uv_addr_lsb8" / u32,
		"hdr_170_width_align" / u32,
		"hdr_174_width_align" / u32,
	)
	def __init__(self):
		super().__init__()

class AvdVP9V3FrameParams(ConstructClass):
	subcon = Struct(
		"pio" / AvdV3PiodmaHeader,
		"hdr" / AvdV3VP9InstHeader,
	)
	def __init__(self):
		super().__init__()

	def __str__(self):
		return ''.join([str(getattr(self, x)) for x in ["hdr"]])
