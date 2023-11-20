#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..fp import *

class AVDH265V3FakeFrameParams(AVDFakeFrameParams):
	def __init__(self):
		super().__init__()

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

class AVDH265V3FrameParams(AVDFrameParams):
	subcon = Struct(
	)
	_ffpcls = AVDH265V3FakeFrameParams
	def __init__(self):
		super().__init__()
