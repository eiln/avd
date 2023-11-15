#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..hal import AVDHal
from ..utils import *
from .fp import *
from .types import *
from copy import deepcopy

def set_bit(n, x=1): return ((x & 1) << n)

class AVDVP9HalV3(AVDHal):
	def __init__(self):
		super().__init__()

	def set_refs(self, ctx, sl):
		avd_set = self.avd_set

		avd_set(0x70007, "cm3_dma_config_7")
		avd_set(0x70007, "cm3_dma_config_8")
		avd_set(0x70007, "cm3_dma_config_9")

		if 0:
			for i,dpb in enumerate(ctx.dpb[:32]):
				print(i, f"[{', '.join([hex(x) for x in dpb])}]")

		hw = (((sl.frame_height - 1) & 0xffff) << 16) | ((sl.frame_width - 1) & 0xffff)

		refidx = 0
		avd_set(0x1000000, "hdr_9c_ref_100", refidx)
		avd_set(hw, "hdr_70_ref_height_width", refidx)
		avd_set(0x40004000, "hdr_7c_ref_align", refidx)
		if (len(ctx.dpb) <= 1):
			dpb = ctx.rvra0_base_addrs
		else:
			dpb = ctx.dpb[-1]
		avd_set(dpb[0], "hdr_138_ref_rvra0_addr_lsb7", refidx)
		avd_set(dpb[1], "hdr_144_ref_rvra1_addr_lsb7", refidx)
		avd_set(dpb[2], "hdr_150_ref_rvra2_addr_lsb7", refidx)
		avd_set(dpb[3], "hdr_15c_ref_rvra3_addr_lsb7", refidx)

		refidx = 1
		avd_set(0x1000000, "hdr_9c_ref_100", refidx)
		avd_set(hw, "hdr_70_ref_height_width", refidx)
		avd_set(0x40004000, "hdr_7c_ref_align", refidx)

		if (sl.idx == 0):
			dpb = ctx.rvra0_base_addrs
		else:
			if (sl.idx <= 10):
				m = 0
			else:
				m = ((((sl.idx - 1) // 10) - 1) * 10) + 2
			dpb = ctx.dpb[m]

		avd_set(dpb[0], "hdr_138_ref_rvra0_addr_lsb7", refidx)
		avd_set(dpb[1], "hdr_144_ref_rvra1_addr_lsb7", refidx)
		avd_set(dpb[2], "hdr_150_ref_rvra2_addr_lsb7", refidx)
		avd_set(dpb[3], "hdr_15c_ref_rvra3_addr_lsb7", refidx)

		refidx = 2
		avd_set(0x1000000, "hdr_9c_ref_100", refidx)
		avd_set(hw, "hdr_70_ref_height_width", refidx)
		avd_set(0x40004000, "hdr_7c_ref_align", refidx)
		dpb = ctx.rvra0_base_addrs
		avd_set(dpb[0], "hdr_138_ref_rvra0_addr_lsb7", refidx)
		avd_set(dpb[1], "hdr_144_ref_rvra1_addr_lsb7", refidx)
		avd_set(dpb[2], "hdr_150_ref_rvra2_addr_lsb7", refidx)
		avd_set(dpb[3], "hdr_15c_ref_rvra3_addr_lsb7", refidx)

	def make_flags1(self, ctx, sl):
		x = 0

		# always set
		x |= set_bit( 0)
		x |= set_bit(14)
		x |= set_bit(15)

		if (sl.frame_type != VP9_FRAME_TYPE_KEY):
			x |= set_bit(19)  # has ref #1
			if (ctx.kidx > 0):
				x |= set_bit(21)  # has ref #2

			x |= set_bit(18, sl.is_filter_switchable)
			if (not sl.is_filter_switchable):
				if (sl.raw_interpolation_filter_type == 0):
					x |= set_bit(16)
				elif (sl.raw_interpolation_filter_type == 2):
					x |= set_bit(17)

		# ???
		if (ctx.kidx < 1) or (ctx.kidx >= 10):
			x |= set_bit(8)
		if (ctx.kidx > 0):
			x |= set_bit(9)  # ?

		if (ctx.kidx % 10 == 0):
			x |= set_bit(4)
		else:
			x |= set_bit(5)

		return x

	def set_header(self, ctx, sl):
		avd_set = self.avd_set
		ctx = deepcopy(ctx) # RO

		assert((ctx.inst_fifo_idx >= 0) and (ctx.inst_fifo_idx <= ctx.inst_fifo_count))
		avd_set(0x2bfff100 + (ctx.inst_fifo_idx * 0x10), "cm3_cmd_inst_fifo_start")
		# ---- FW BP ----

		x = 0x2db012e0
		if (sl.frame_type == VP9_FRAME_TYPE_KEY):
			x |= 0x2000
		avd_set(x, "hdr_30_cmd_start_hdr")

		avd_set(0x2000000, "hdr_34_const_20")
		avd_set((((sl.frame_height - 1) & 0xffff) << 16) | ((sl.frame_width - 1) & 0xffff), "hdr_28_height_width_shift3")
		avd_set(0x0, "cm3_dma_config_0")
		avd_set((((sl.frame_height - 1) & 0xffff) << 16) | ((sl.frame_width - 1) & 0xffff), "hdr_38_height_width_shift3")

		x = 0x1000000
		x |= 0x1800 | (min(sl.txfm_mode, 3) << 7)
		avd_set(x | (sl.txfm_mode == 4), "hdr_2c_txfm_mode")

		avd_set(self.make_flags1(ctx, sl), "hdr_40_flags1_pt1")

		for n in range(8):
			avd_set(0x0)

		avd_set(0x20000, "cm3_dma_config_1")
		avd_set(0x4020002, "cm3_dma_config_2")
		avd_set(0x2020202, "cm3_dma_config_3")
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
		# ---- FW BP ----

		avd_set(sl.base_q_idx * 0x8000, "hdr_4c_base_q_idx")
		avd_set(0b1000000011111111111111, "hdr_44_flags1_pt2")
		avd_set(sl.loop_filter_level * 0x4000, "hdr_48_loop_filter_level")

		avd_set(0x4020002, "cm3_dma_config_4")
		avd_set(0x4020002, "cm3_dma_config_5")
		avd_set(0x0, "cm3_dma_config_6")

		sps_size = 0x8000 >> 8
		avd_set((ctx.sps_tile_base_addr + (0 * sps_size)), "hdr_e8_sps0_tile_addr_lsb8", 0)
		avd_set((ctx.sps_tile_base_addr + (1 * sps_size)), "hdr_e8_sps0_tile_addr_lsb8", 1)
		avd_set((ctx.sps_tile_base_addr + (2 * sps_size)) * 0, "hdr_e8_sps0_tile_addr_lsb8", 2) # zeroed
		avd_set((ctx.sps_tile_base_addr + (3 * sps_size)), "hdr_f4_sps1_tile_addr_lsb8", 0)
		avd_set((ctx.sps_tile_base_addr + (4 * sps_size)), "hdr_f4_sps1_tile_addr_lsb8", 1)
		avd_set((ctx.sps_tile_base_addr + (6 * sps_size)), "hdr_f4_sps1_tile_addr_lsb8", 3) # not 5, that's later

		avd_set(0x70007, "cm3_dma_config_7")
		avd_set(ctx.curr_rvra_addrs[0], "hdr_11c_curr_rvra_addr_lsb7", 0)
		avd_set(ctx.curr_rvra_addrs[1], "hdr_11c_curr_rvra_addr_lsb7", 1)
		avd_set(ctx.curr_rvra_addrs[2], "hdr_11c_curr_rvra_addr_lsb7", 2)
		avd_set(ctx.curr_rvra_addrs[3], "hdr_11c_curr_rvra_addr_lsb7", 3)

		avd_set((ctx.sps_tile_base_addr + (5 * sps_size)), "hdr_f4_sps1_tile_addr_lsb8", 2)

		avd_set(ctx.y_addr >> 8, "hdr_168_y_addr_lsb8")

		avd_set(ctx.height_width_align, "hdr_170_width_align")
		avd_set(ctx.uv_addr >> 8, "hdr_16c_uv_addr_lsb8")
		avd_set(ctx.height_width_align, "hdr_174_width_align")
		avd_set(0x0)
		avd_set((((sl.frame_height - 1) & 0xffff) << 16) | ((sl.frame_width - 1) & 0xffff), "cm3_height_width")

		if (sl.frame_type != VP9_FRAME_TYPE_KEY):
			self.set_refs(ctx, sl)

		# ---- FW BP ----

	def set_tiles(self, ctx, sl):
		avd_set = self.avd_set
		# tiles instead of slice for VP9
		for i,tile in enumerate(sl.tiles):
			avd_set(0x2d800000, "cm3_cmd_set_slice_data")
			avd_set(ctx.slice_data_addr + tile.offset, "til_ab4_tile_addr_low")
			avd_set(tile.size, "til_ab8_tile_size")
			avd_set(0x2a000000 | i * 4)
			if (len(sl.tiles) == 1):
				dims = 1
			else:
				dims = i << 24 | ((tile.row + 1) * 8 - 1) << 12 | ((tile.col + 1) * 4 - 1)
			avd_set(dims, "til_ac0_tile_dims")
			if (i < len(sl.tiles) - 1):
				avd_set(0x2bfff000, "cm3_cmd_inst_fifo_end")
			else:
				avd_set(0x2b000400, "cm3_cmd_inst_fifo_end")

	def set_insn(self, ctx, sl):
		self.set_header(ctx, sl)
		self.set_tiles(ctx, sl)
