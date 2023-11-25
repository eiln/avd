#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..hal import AVDHal
from ..utils import *
from .fp import *
from .types import *
from copy import deepcopy

class AVDVP9HalV3(AVDHal):
	def __init__(self):
		super().__init__()

	def get_rvra_addrs(self, ctx, sl, idx):
		x = idx
		n = x
		m = x
		rvra_addrs = [0] * 4
		rvra_addrs[0] = ctx.rvra0_addrs[n]
		rvra_addrs[1] = ctx.rvra1_addrs[m]
		rvra_addrs[2] = ctx.rvra2_addrs[n]
		rvra_addrs[3] = ctx.rvra3_addrs[m]
		return rvra_addrs

	def set_refs(self, ctx, sl):
		push = self.push

		push(0x70007, "cm3_dma_config_7")
		push(0x70007, "cm3_dma_config_8")
		push(0x70007, "cm3_dma_config_9")

		hw = (((sl.frame_height - 1) & 0xffff) << 16) | ((sl.frame_width - 1) & 0xffff)
		for n in range(VP9_REFS_PER_FRAME):
			push(0x1000000, "hdr_9c_ref_100", n)
			push(hw, "hdr_70_ref_height_width", n)
			push(0x40004000, "hdr_7c_ref_align", n)

			x = ctx.ref_frame_map[n]
			rvra_addrs = self.get_rvra_addrs(ctx, sl, x)
			push(rvra_addrs[0], "hdr_138_ref_rvra0_addr_lsb7", n)
			push(rvra_addrs[1], "hdr_144_ref_rvra1_addr_lsb7", n)
			push(rvra_addrs[2], "hdr_150_ref_rvra2_addr_lsb7", n)
			push(rvra_addrs[3], "hdr_15c_ref_rvra3_addr_lsb7", n)

	def make_flags1(self, ctx, sl):
		x = 0

		# always set. just random ones to see if it breaks
		x |= set_bit( 0, sl.show_existing_frame == 0)
		x |= set_bit(14, sl.error_resilient_mode == 0)
		x |= set_bit(15, sl.show_frame)

		if (sl.frame_type != VP9_FRAME_TYPE_KEY):
			x |= set_bit(19)  # has ref #1
			if (ctx.kidx > 0):
				x |= set_bit(21)  # has ref #2

			if (not sl.is_filter_switchable):
				if (sl.raw_interpolation_filter_type == 0):
					x |= set_bit(16)
				elif (sl.raw_interpolation_filter_type == 2):
					x |= set_bit(17)
			x |= set_bit(18, sl.is_filter_switchable)

		if (ctx.last_flag == 0b11) or (ctx.kidx < 1):
			x |= set_bit(4)
		else:
			x |= set_bit(5)

		if (ctx.acc_refresh_mask & (1 << 1)) or (ctx.kidx < 1):
			x |= set_bit(8)
		if (ctx.acc_refresh_mask & (1 << 0)):
			x |= set_bit(9)

		return x

	def set_header(self, ctx, sl):
		push = self.push
		ctx = deepcopy(ctx) # RO

		assert((ctx.inst_fifo_idx >= 0) and (ctx.inst_fifo_idx <= ctx.inst_fifo_count))
		push(0x2bfff100 + (ctx.inst_fifo_idx * 0x10), "cm3_cmd_inst_fifo_start")
		# ---- FW BP ----

		x = 0x2db012e0
		if (sl.frame_type == VP9_FRAME_TYPE_KEY):
			x |= 0x2000
		push(x, "hdr_30_cmd_start_hdr")

		push(0x2000000, "hdr_34_const_20")
		push((((sl.frame_height - 1) & 0xffff) << 16) | ((sl.frame_width - 1) & 0xffff), "hdr_28_height_width_shift3")
		push(0x0, "cm3_dma_config_0")
		push((((sl.frame_height - 1) & 0xffff) << 16) | ((sl.frame_width - 1) & 0xffff), "hdr_38_height_width_shift3")

		x = 0x1000000
		x |= 0x1800 | (min(sl.txfm_mode, 3) << 7)
		push(x | (sl.txfm_mode == 4), "hdr_2c_txfm_mode")

		push(self.make_flags1(ctx, sl), "hdr_40_flags1_pt1")

		for n in range(8):
			push(0x0)

		push(0x20000, "cm3_dma_config_1")
		push(0x4020002, "cm3_dma_config_2")
		push(0x2020202, "cm3_dma_config_3")
		push(0x240, "hdr_e0_const_240")
		push(ctx.probs_addr >> 8, "hdr_104_probs_addr_lsb8")

		push(ctx.pps0_tile_addr, "hdr_118_pps0_tile_addr_lsb8")
		n = ((ctx.access_idx // 128) + 1) % 8
		push(ctx.pps1_tile_addrs[n], "hdr_108_pps1_tile_addr_lsb8", 0)
		push(ctx.pps1_tile_addrs[n], "hdr_108_pps1_tile_addr_lsb8", 1)

		if (sl.frame_type == VP9_FRAME_TYPE_KEY):
			n = not (ctx.num_kf) & 1
			m = not (ctx.num_kf) & 1
		elif (ctx.last_kf):
			n = (ctx.num_kf) & 1
			m = not (ctx.num_kf) & 1
		else:
			n = (ctx.kidx + ctx.num_kf) & 1
			m = not (ctx.kidx + ctx.num_kf) & 1
		push(ctx.pps2_tile_addrs[n], "hdr_110_pps2_tile_addr_lsb8", 0)
		push(ctx.pps2_tile_addrs[m], "hdr_110_pps2_tile_addr_lsb8", 1)
		# ---- FW BP ----

		push(sl.base_q_idx * 0x8000, "hdr_4c_base_q_idx")
		push(0b1000000011111111111111, "hdr_44_flags1_pt2")
		push(sl.loop_filter_level * 0x4000, "hdr_48_loop_filter_level")

		push(0x4020002, "cm3_dma_config_4")
		push(0x4020002, "cm3_dma_config_5")
		push(0x0, "cm3_dma_config_6")

		sps_size = 0x8000 >> 8
		push((ctx.sps_tile_base_addr + (0 * sps_size)), "hdr_e8_sps0_tile_addr_lsb8", 0)
		push((ctx.sps_tile_base_addr + (1 * sps_size)), "hdr_e8_sps0_tile_addr_lsb8", 1)
		push((ctx.sps_tile_base_addr + (2 * sps_size)) * 0, "hdr_e8_sps0_tile_addr_lsb8", 2) # zeroed
		push((ctx.sps_tile_base_addr + (3 * sps_size)), "hdr_f4_sps1_tile_addr_lsb8", 0)
		push((ctx.sps_tile_base_addr + (4 * sps_size)), "hdr_f4_sps1_tile_addr_lsb8", 1)
		push((ctx.sps_tile_base_addr + (6 * sps_size)), "hdr_f4_sps1_tile_addr_lsb8", 3) # not 5, that's later

		push(0x70007, "cm3_dma_config_7")

		x = ctx.new_fb_idx
		rvra_addrs = self.get_rvra_addrs(ctx, sl, x)
		push(rvra_addrs[0], "hdr_11c_curr_rvra_addr_lsb7", 0)
		push(rvra_addrs[1], "hdr_11c_curr_rvra_addr_lsb7", 1)
		push(rvra_addrs[2], "hdr_11c_curr_rvra_addr_lsb7", 2)
		push(rvra_addrs[3], "hdr_11c_curr_rvra_addr_lsb7", 3)

		push((ctx.sps_tile_base_addr + (5 * sps_size)), "hdr_f4_sps1_tile_addr_lsb8", 2)

		push(ctx.y_addr >> 8, "hdr_168_y_addr_lsb8")
		push(ctx.height_width_align, "hdr_170_width_align")
		push(ctx.uv_addr >> 8, "hdr_16c_uv_addr_lsb8")
		push(ctx.height_width_align, "hdr_174_width_align")
		push(0x0)
		push((((sl.frame_height - 1) & 0xffff) << 16) | ((sl.frame_width - 1) & 0xffff), "cm3_height_width")

		if (sl.frame_type != VP9_FRAME_TYPE_KEY):
			self.set_refs(ctx, sl)

		# ---- FW BP ----

	def set_tiles(self, ctx, sl):
		push = self.push
		# tiles instead of slice for VP9
		for i,tile in enumerate(sl.tiles):
			push(0x2d800000, "cm3_cmd_set_slice_data")
			push(ctx.slice_data_addr + tile.offset, "til_ab4_tile_addr_low")
			push(tile.size, "til_ab8_tile_size")
			push(0x2a000000 | i * 4)
			if (len(sl.tiles) == 1):
				dims = 1
			else:
				dims = i << 24 | ((tile.row + 1) * 8 - 1) << 12 | ((tile.col + 1) * 4 - 1)
			push(dims, "til_ac0_tile_dims")
			if (i < len(sl.tiles) - 1):
				push(0x2bfff000, "cm3_cmd_inst_fifo_end")
			else:
				push(0x2b000400, "cm3_cmd_inst_fifo_end")

	def set_insn(self, ctx, sl):
		self.set_header(ctx, sl)
		self.set_tiles(ctx, sl)
