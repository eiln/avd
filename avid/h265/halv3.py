#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..hal import AVDHal
from ..utils import *
from .types import *

class AVDH265HalV3(AVDHal):
	def __init__(self):
		super().__init__()

	def get_pps(self, ctx, sl):
		return ctx.pps_list[sl.slice_pic_parameter_set_id]

	def get_sps(self, ctx, sl):
		return ctx.sps_list[self.get_pps(ctx, sl).pps_seq_parameter_set_id]

	def rvra_offset(self, ctx, idx):
		if   (idx == 0): return ctx.rvra_size0
		elif (idx == 1): return 0
		elif (idx == 2): return ctx.rvra_size0 + ctx.rvra_size1 + ctx.rvra_size2
		elif (idx == 3): return ctx.rvra_size0 + ctx.rvra_size1
		raise ValueError("invalid rvra group (%d)" % idx)

	def set_refs(self, ctx, sl):
		push = self.push

		push(0x4020002, "cm3_dma_config_6")
		push(ctx.pps_tile_addrs[1] >> 8, "hdr_dc_pps_tile_addr_lsb8", 6)

		n = (ctx.access_idx + 2) % 16
		push(ctx.sps_tile_addrs[n] >> 8, "hdr_bc_sps_tile_addr_lsb8")
		#push(0xdead, "hdr_bc_sps_tile_addr_lsb8")

		push(0x70007, "cm3_dma_config_7")
		push(0x70007, "cm3_dma_config_8")
		push(0x70007, "cm3_dma_config_9")
		push(0x70007, "cm3_dma_config_a")

		pred = sl.pic.poc
		for n,rvra in enumerate(ctx.dpb_list):
			if (n == 0):
				delta_base = 0
			else:
				delta_base = ctx.dpb_list[n-1].poc
			delta = delta_base - rvra.poc
			pred = pred + delta
			x = ((len(ctx.dpb_list) - 1) * 0x10000000) | 0x1000000 | swrap(pred, 0x20000)
			push(x, "hdr_114_ref_hdr", n)
			push((rvra.addr + self.rvra_offset(ctx, 0)) >> 7, "hdr_134_ref0_addr_lsb7", n)
			push((rvra.addr + self.rvra_offset(ctx, 1)) >> 7, "hdr_154_ref1_addr_lsb7", n)
			push((rvra.addr + self.rvra_offset(ctx, 2)) >> 7, "hdr_174_ref2_addr_lsb7", n)
			push((rvra.addr + self.rvra_offset(ctx, 3)) >> 7, "hdr_194_ref3_addr_lsb7", n)

	def set_flags(self, ctx, sl):
		push = self.push

		x = 0
		push(x, "hdr_30_flag_pt1")

		x = 0
		x |= set_bit(3)
		x |= set_bit(9)
		push(x, "hdr_34_flag_pt2")

		x = 0
		x |= set_bit(3)
		x |= set_bit(4)
		x |= set_bit(16)
		x |= set_bit(17)
		x |= set_bit(20)
		if (not IS_INTRA(sl)):
			x |= set_bit(21)
		push(x, "hdr_5c_flag_pt3")

		push(0, "hdr_60_zero")
		push(0, "hdr_64_zero")
		push(0, "hdr_68_zero")
		push(0, "hdr_6c_zero")
		push(0, "hdr_70_zero")
		push(0, "hdr_74_zero")
		push(0, "hdr_78_zero")

	def set_header(self, ctx, sl):
		push = self.push

		assert((ctx.inst_fifo_idx >= 0) and (ctx.inst_fifo_idx <= ctx.inst_fifo_count))
		push(0x2b000000 | 0x100 | (ctx.inst_fifo_idx * 0x10), "cm3_cmd_inst_fifo_start")
		# ---- FW BP -----

		x = 0x1000
		if (IS_INTRA(sl)):
			x |= 0x2000
		x |= 0x2e0
		push(0x2db00000 | x, "hdr_4c_cmd_start_hdr")

		push(0x0000000, "hdr_50_mode")
		push((((ctx.height - 1) & 0xffff) << 16) | ((ctx.width - 1) & 0xffff), "hdr_54_height_width")
		push(0x0, "hdr_58_pixfmt_zero")
		push((((ctx.height - 1) >> 3) << 16) | ((ctx.width - 1) >> 3), "hdr_28_height_width_shift3")

		x = 0x1000000 * self.get_sps(ctx, sl).chroma_format_idc | 0x1000 | 0x800
		x |= (3 << 7) | 0  # 265 is always up to 32x32 txfm | txfm !specified for each block
		push(x, "hdr_2c_sps_param")

		self.set_flags(ctx, sl)
		push(0x300000, "hdr_98_const_30")
		push(0x4020002, "cm3_dma_config_1")
		push(0x20002, "cm3_dma_config_2")
		push(0x0, "cm3_mark_end_section")
		# ---- FW BP -----

		push(0x4020002, "cm3_dma_config_3")
		push(0x4020002, "cm3_dma_config_4")
		push(0x0)
		push(ctx.pps_tile_addrs[0] >> 8, "hdr_dc_pps_tile_addr_lsb8", 0)
		push(ctx.pps_tile_addrs[2] >> 8, "hdr_dc_pps_tile_addr_lsb8", 1)
		push(ctx.pps_tile_addrs[3] >> 8, "hdr_dc_pps_tile_addr_lsb8", 2)
		push(0x0)
		push(0x0)
		push(ctx.pps_tile_addrs[4] >> 8, "hdr_dc_pps_tile_addr_lsb8", 8)
		push(0x0)

		push(0x70007, "cm3_dma_config_5")

		x = sl.pic.addr
		push((x + self.rvra_offset(ctx, 0)) >> 7, "hdr_104_curr_ref_addr_lsb7", 0)
		push((x + self.rvra_offset(ctx, 1)) >> 7, "hdr_104_curr_ref_addr_lsb7", 1)
		push((x + self.rvra_offset(ctx, 2)) >> 7, "hdr_104_curr_ref_addr_lsb7", 2)
		push((x + self.rvra_offset(ctx, 3)) >> 7, "hdr_104_curr_ref_addr_lsb7", 3)
		push(0x0, "cm3_mark_end_section")

		push(ctx.y_addr >> 8, "hdr_1b4_y_addr_lsb8")
		push((round_up(ctx.width, 64) >> 6) << 2, "hdr_1bc_width_align")
		push(ctx.uv_addr >> 8, "hdr_1b8_uv_addr_lsb8")
		push((round_up(ctx.width, 64) >> 6) << 2, "hdr_1c0_width_align")
		push(0x0, "cm3_mark_end_section")
		push((((ctx.height - 1) & 0xffff) << 16) | ((ctx.width - 1) & 0xffff), "hdr_54_height_width")

		if (not IS_INTRA(sl)):
			self.set_refs(ctx, sl)

		push(0x0, "cm3_mark_end_section")
		# ---- FW BP -----

	def set_weights(self, ctx, sl):
		push = self.push

		x = 0x2dd00000
		if (sl.has_luma_weights == 0):
			push(x, "slc_b08_cmd_weights_denom")
			return
		if (sl.slice_type == HEVC_SLICE_P):
			x |= 0x40
		else:
			x |= 0xad
		x |= (sl.luma_log2_weight_denom << 3) | sl.chroma_log2_weight_denom
		push(x, "slc_b08_cmd_weights_denom")

		def get_wbase(i, j): return 0x2de00000 | ((j + 1) * 0x4000) | (i * 0x200)
		num = 0
		for i in range(sl.num_ref_idx_l0_active_minus1 + 1):
			if (sl.luma_weight_l0_flag[i]):
				push(get_wbase(i, 0) | sl.luma_weight_l0[i], "slc_b0c_cmd_weights_weights", num)
				push(0x2df00000 | swrap(sl.luma_offset_l0[i], 0x10000), "slc_b6c_cmd_weights_offsets", num)
				num += 1
			if (sl.chroma_weight_l0_flag[i]):
				push(get_wbase(i, 1) | sl.chroma_weight_l0[i][0], "slc_b0c_cmd_weights_weights", num)
				push(0x2df00000 | swrap(sl.chroma_offset_l0[i][0], 0x10000), "slc_b6c_cmd_weights_offsets", num)
				num += 1
				push(get_wbase(i, 2) | sl.chroma_weight_l0[i][1], "slc_b0c_cmd_weights_weights", num)
				push(0x2df00000 | swrap(sl.chroma_offset_l0[i][1], 0x10000), "slc_b6c_cmd_weights_offsets", num)
				num += 1

		if (sl.slice_type == HEVC_SLICE_B):
			for i in range(sl.num_ref_idx_l1_active_minus1 + 1):
				if (sl.luma_weight_l1_flag[i]):
					push(get_wbase(i, 0) | sl.luma_weight_l1[i], "slc_b0c_cmd_weights_weights", num)
					push(0x2df00000 | swrap(sl.luma_offset_l1[i], 0x10000), "slc_b6c_cmd_weights_offsets", num)
					num += 1
				if (sl.chroma_weight_l1_flag[i]):
					push(get_wbase(i, 1) | sl.chroma_weight_l1[i][0], "slc_b0c_cmd_weights_weights", num)
					push(0x2df00000 | swrap(sl.chroma_offset_l1[i][0], 0x10000), "slc_b6c_cmd_weights_offsets", num)
					num += 1
					push(get_wbase(i, 2) | sl.chroma_weight_l1[i][1], num)
					push(0x2df00000 | swrap(sl.chroma_offset_l1[i][1], 0x10000), "slc_b6c_cmd_weights_offsets", num)
					num += 1

	def set_slice(self, ctx, sl):
		push = self.push
		push(0x2d800000 | 0x6000, "cm3_cmd_set_coded_slice")
		push(ctx.slice_data_addr + sl.get_payload_offset(), "slc_bd8_slice_addr")
		push(sl.get_payload_size(), "slc_bdc_slice_size")
		push(0x2c000000, "cm3_cmd_exec_mb_vp")
		# ---- FW BP -----

		push(0x2d900000 | ((26 + self.get_pps(ctx, sl).pic_init_qp_minus26 + sl.slice_qp_delta) * 0x400), "slc_bcc_cmd_slice_qp")

		x = 0
		x |= set_bit(6)
		x |= set_bit(7)
		x |= set_bit(16)
		if (sl.slice_loop_filter_across_slices_enabled_flag):
			x |= set_bit(17)
		x |= set_bit(18)
		push(0x2da00000 | x, "slc_bd0_cmd_flags")

		if (sl.slice_type == HEVC_SLICE_P) or (sl.slice_type == HEVC_SLICE_B):
			num = 0
			lx = 0
			for i,lst in enumerate(sl.reflist[0]):
				pos = list([x.poc for x in ctx.dpb_list]).index(lst.poc)
				push(0x2dc00000 | (lx << 8) | (i << 4) | pos, "slc_a90_cmd_ref_list", i)
				num += 1
			if (sl.slice_type == HEVC_SLICE_B):
				lx = 1
				for i,lst in enumerate(sl.reflist[1]):
					pos = list([x.poc for x in ctx.dpb_list]).index(lst.poc)
					push(0x2dc00000 | (lx << 8) | (i << 4) | pos,
					"slc_a90_cmd_ref_list", num + i)

			self.set_weights(ctx, sl)

		push(0x2a000000, "cm3_cmd_set_mb_dims")
		push(0x1, "cm3_set_mb_dims") # ?

		x = 0x2d000000
		if   (sl.slice_type == HEVC_SLICE_I):
			x |= 0x20000
		elif (sl.slice_type == HEVC_SLICE_P):
			x |= 0x10000
		elif (sl.slice_type == HEVC_SLICE_B):
			x |= 0x40000

		if ((sl.slice_type == HEVC_SLICE_P) or (sl.slice_type == HEVC_SLICE_B)):
			x |= 0x6
			x |= 0x8000
			if (sl.num_ref_idx_active_override_flag):
				x |= 0x40000
			x |= sl.num_ref_idx_l0_active_minus1 << 11
			if (sl.slice_type == HEVC_SLICE_B):
				x |= 0x50
				x |= sl.num_ref_idx_l1_active_minus1 << 7
		push(x, "slc_a8c_cmd_ref_type")

		if ((sl.slice_type == HEVC_SLICE_P) and not ctx.last_intra) or (sl.slice_type == HEVC_SLICE_B):
			n = ctx.access_idx % 16
			push(ctx.sps_tile_addrs[n] >> 8, "slc_bd4_sps_tile_addr2_lsb8")
			#push(0xbeef, "slc_bd4_sps_tile_addr2_lsb8")
		push(0x1000000, "slc_be0_unk_100")

		push(0x2b000000 | 0x400, "cm3_cmd_inst_fifo_end")

	def set_insn(self, ctx, sl):
		self.set_header(ctx, sl)
		self.set_slice(ctx, sl)
