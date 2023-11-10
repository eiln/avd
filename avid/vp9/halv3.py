#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..hal import AVDHal
from ..utils import *
from .fp import *
from .types import *

class AVDVP9HalV3(AVDHal):
	def __init__(self, ctx=None):
		super().__init__(ctx=ctx)

	def set_refs(self, ctx, sl):
		avd_set = self.avd_set

		avd_set(0x70007, "fw_dma_config_7")
		avd_set(0x70007, "fw_dma_config_8")
		avd_set(0x70007, "fw_dma_config_9")

		for n in range(2):
			avd_set(0x1000000)
			avd_set(0x3f007f)
			avd_set(0x40004000)

			avd_set(0xef80) # rvra
			avd_set(0xeb82)
			avd_set(0xf080)
			avd_set(0xec12)

	def get_n(self, ctx):
		i = ctx.access_idx
		if (i == 0): return 0
		if (i <= 11): return int((not i & 1))
		if (i <= 21): return int((not i & 1)) * 2
		if (i <= 31): return int((not i & 1)) * 3
		if (i <= 41): return int((not i & 1)) * 4
		if (i <= 51): return int((not i & 1)) * 5

	def set_header(self, ctx, sl):
		avd_set = self.avd_set

		assert((ctx.inst_fifo_idx >= 0) and (ctx.inst_fifo_idx <= ctx.inst_fifo_count))
		avd_set(0x2bfff100 + (ctx.inst_fifo_idx * 0x10), "fw_cmd_inst_fifo_start")
		#print("x: 0x%x y: 0x%x" % (avd_r32(0x1104020), avd_r32(0x1104034))) FW BP

		x = 0x2db012e0
		if (sl.frame_type == VP9_FRAME_TYPE_KEY):
			x |= 0x2000
		avd_set(x, "hdr_30_cmd_start_hdr")

		avd_set(0x2000000, "hdr_34_const_20")
		avd_set((((sl.frame_height - 1) & 0xffff) << 16) | ((sl.frame_width - 1) & 0xffff), "hdr_28_height_width_shift3")
		avd_set(0x0, "fw_dma_config_0")
		avd_set((((sl.frame_height - 1) & 0xffff) << 16) | ((sl.frame_width - 1) & 0xffff), "hdr_38_height_width_shift3")
		avd_set(0x1001980, "hdr_2c_sps_param")

		avd_set(0xc111, "hdr_40_flags1_pt1")
		for n in range(8):
			avd_set(0x0)

		avd_set(0x20000, "fw_dma_config_1")
		avd_set(0x4020002, "fw_dma_config_2")
		avd_set(0x2020202, "fw_dma_config_3")
		avd_set(0x240, "hdr_e0_const_240")

		avd_set(ctx.probs_addr >> 8, "hdr_104_probs_addr_lsb8")

		avd_set(ctx.pps_tile_addrs[0], "hdr_118_pps0_tile_addr_lsb8")
		avd_set(ctx.pps_tile_addrs[1], "hdr_108_pps1_tile_addr_lsb8", 0)
		avd_set(ctx.pps_tile_addrs[1], "hdr_108_pps1_tile_addr_lsb8", 1)
		if (sl.frame_type == VP9_FRAME_TYPE_KEY):
			n = 2
			m = 2
		else:
			if (not ctx.access_idx & 1):
				n = 2
				m = 3
			else:
				n = 3
				m = 2
		avd_set(ctx.pps_tile_addrs[n], "hdr_108_pps1_tile_addr_lsb8", 2)
		avd_set(ctx.pps_tile_addrs[m], "hdr_108_pps1_tile_addr_lsb8", 3)
		#print("x: 0x%x y: 0x%x" % (avd_r32(0x1104020), avd_r32(0x1104034))) FW BP

		avd_set(0x128000, "hdr_48_flags2_pt2")
		avd_set(0x203fff, "hdr_44_flags1_pt2")
		avd_set(0x0, "hdr_4c_flags2_pt2")

		avd_set(0x4020002, "fw_dma_config_4")
		avd_set(0x4020002, "fw_dma_config_5")
		avd_set(0x0, "fw_dma_config_6")

		size = 0x8000 >> 8
		avd_set((ctx.sps_tile_base_addr + (0 * size)), "hdr_e8_sps0_tile_addr_lsb8", 0)
		avd_set((ctx.sps_tile_base_addr + (1 * size)), "hdr_e8_sps0_tile_addr_lsb8", 1)
		avd_set((ctx.sps_tile_base_addr + (2 * size)) * 0, "hdr_e8_sps0_tile_addr_lsb8", 2) # zeroed
		avd_set((ctx.sps_tile_base_addr + (3 * size)), "hdr_f4_sps1_tile_addr_lsb8", 0)
		avd_set((ctx.sps_tile_base_addr + (4 * size)), "hdr_f4_sps1_tile_addr_lsb8", 1)
		avd_set((ctx.sps_tile_base_addr + (6 * size)), "hdr_f4_sps1_tile_addr_lsb8", 3) # not 5, that's later

		avd_set(0x70007, "fw_dma_config_7")

		if (sl.frame_type == VP9_FRAME_TYPE_KEY):
			rvra_addrs = ctx.rvra0_addrs
		else:
			n = self.get_n(ctx)
			rvra_addrs = getattr(ctx, "rvra%d_addrs" % (n + 1))
		avd_set(rvra_addrs[0], "hdr_11c_curr_rvra_addr_lsb7", 0)
		avd_set(rvra_addrs[1], "hdr_11c_curr_rvra_addr_lsb7", 1)
		avd_set(rvra_addrs[2], "hdr_11c_curr_rvra_addr_lsb7", 2)
		avd_set(rvra_addrs[3], "hdr_11c_curr_rvra_addr_lsb7", 3)

		avd_set((ctx.sps_tile_base_addr + (5 * size)), "hdr_f4_sps1_tile_addr_lsb8", 2)

		avd_set(ctx.y_addr >> 8, "hdr_168_y_addr_lsb8")
		avd_set(0xc, "hdr_170_width_align")
		avd_set(ctx.uv_addr >> 8, "hdr_16c_uv_addr_lsb8")
		avd_set(0xc, "hdr_174_width_align")
		avd_set(0x0)
		avd_set((((sl.frame_height - 1) & 0xffff) << 16) | ((sl.frame_width - 1) & 0xffff), "fw_height_width")

		if (sl.frame_type != VP9_FRAME_TYPE_KEY):
			self.set_refs(ctx, sl)

		#print("x: 0x%x y: 0x%x" % (avd_r32(0x1104020), avd_r32(0x1104034))) FW BP

	def set_slice(self, ctx, sl):
		avd_set = self.avd_set
		avd_set(0x2d800000, "fw_cmd_set_slice_data")
		header_size = sl.compressed_header_size + sl.uncompressed_header_size
		payload_size = sl.frame.size - header_size
		avd_set(ctx.slice_data_addr + header_size, "inp_8b4d4_slice_addr_low")
		avd_set(payload_size, "inp_8b4d8_slice_hdr_size")

		avd_set(0x2a000000)
		avd_set(0x1)
		avd_set(0x2b000400, "fw_cmd_inst_fifo_end")

	def generate(self, ctx, sl):
		self.inst_stream = []
		self.fp = AVDVP9V3FakeFrameParams.new()
		self.set_header(ctx, sl)
		self.set_slice(ctx, sl)
		return self.inst_stream
