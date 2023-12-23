#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..hal import AVDHal
from ..utils import *
from .types import *

class AVDH265HalV3(AVDHal):
	def __init__(self):
		super().__init__()

	def get_cond(self, ctx, sl):
		pps = ctx.get_pps(sl)
		has_slices = (((sl.first_slice_segment_in_pic_flag) and len(sl.slices)) or (not sl.first_slice_segment_in_pic_flag))
		has_tiles = (pps.tiles_enabled_flag) and (sl.num_entry_point_offsets > 0)
		cond = (not has_slices) and (not has_tiles)
		cond = cond or (sl.slice_type == HEVC_SLICE_B)
		return cond

	def set_scaling_list(self, ctx, sl, list_4x4, list_8x8, list_16x16, list_32x32,
							   mask, dc_coef, is_sps):
		push = self.push

		for i in range(2):
			for j in range(2):
				x =  dc_coef[i][j*3 + 0] << 16
				x |= dc_coef[i][j*3 + 1] << 8
				x |= dc_coef[i][j*3 + 2] << 0
				push(x, "hdr_%x_sps_scl_delta_coeff" % (0x3c + (i*2 + j)*4) if is_sps
						else "hdr_%x_pps_scl_delta_coeff" % (0x80 + (i*2 + j)*4))

		for i in range(6): # 4x4: transposed in stride 4
			if (mask & (1 << (0*6 + i))):
				for j in range(16 // 4):
					x = 0
					x |= list_4x4[i][j + 0*4] << 24
					x |= list_4x4[i][j + 1*4] << 16
					x |= list_4x4[i][j + 2*4] << 8
					x |= list_4x4[i][j + 3*4] << 0
					push(x, "scl_22c_seq_scaling_matrix_4x4" if is_sps else "scl_610_pic_scaling_matrix_4x4", i*(16 // 4) + j)

		for i in range(6): # 8x8: transposed in stride 8
			if (mask & (1 << (1*6 + i))):
				for j in range(2):
					for k in range(8):
						x = 0
						x |= list_8x8[i][j*32 + k + 0*8] << 24
						x |= list_8x8[i][j*32 + k + 1*8] << 16
						x |= list_8x8[i][j*32 + k + 2*8] << 8
						x |= list_8x8[i][j*32 + k + 3*8] << 0
						push(x, "scl_28c_seq_scaling_matrix_8x8" if is_sps else "scl_670_pic_scaling_matrix_8x8", i*(64 // 4) + j*8 + k)

		for i in range(6): # 16x16: transposed in stride 8
			if (mask & (1 << (2*6 + i))):
				for j in range(2):
					for k in range(8):
						x = 0
						x |= list_16x16[i][j*32 + k + 0*8] << 24
						x |= list_16x16[i][j*32 + k + 1*8] << 16
						x |= list_16x16[i][j*32 + k + 2*8] << 8
						x |= list_16x16[i][j*32 + k + 3*8] << 0
						push(x, "scl_40c_seq_scaling_matrix_16x16" if is_sps else "scl_7f0_pic_scaling_matrix_16x16", i*(64 // 4) + j*8 + k)

		for i in range(6): # 32x32: transposed in stride 8
			if (i not in [0, 3]): continue
			if (mask & (1 << (3*6 + i))):
				for j in range(2):
					for k in range(8):
						x = 0
						x |= list_32x32[i][j*32 + k + 0*8] << 24
						x |= list_32x32[i][j*32 + k + 1*8] << 16
						x |= list_32x32[i][j*32 + k + 2*8] << 8
						x |= list_32x32[i][j*32 + k + 3*8] << 0
						push(x, "scl_58c_seq_scaling_matrix_32x32" if is_sps else "scl_970_pic_scaling_matrix_32x32", boolify(i)*(64 // 4) + j*8 + k)

	def set_scaling_lists(self, ctx, sl):
		push = self.push
		sps = ctx.get_sps(sl)
		pps = ctx.get_pps(sl)

		if (not (sps.scaling_list_enable_flag)):
			push(0x0, "cm3_mark_end_section")
			return

		mask = 0
		if (pps.pps_scaling_list_data_present_flag): # Takes precedence if both SPS/PPS
			for i in range(4):
				for j in range(6):
					mask |= set_bit(i*6 + j)  # Set unconditionally
		elif (sps.sps_scaling_list_data_present_flag):
			for i in range(4):
				for j in range(6):
					if (((sps.seq_scaling_list_pred_mode_flag[i][j]) or (sps.seq_scaling_list_pred_matrix_id_delta[i][j])) or (i == 3)):
						mask |= set_bit(i*6 + j)  # Set if !default || size_id == 3

		if (pps.pps_scaling_list_data_present_flag):
			push(0x127ffff, "hdr_7c_pps_scl_dims")
			self.set_scaling_list(ctx, sl, pps.pic_scaling_list_4x4, pps.pic_scaling_list_8x8,
				pps.pic_scaling_list_16x16, pps.pic_scaling_list_32x32, mask,
				pps.pic_scaling_list_delta_coeff, 0)
		elif (sps.sps_scaling_list_data_present_flag):
			push(0x127b377, "hdr_38_sps_scl_dims")
			self.set_scaling_list(ctx, sl, sps.seq_scaling_list_4x4, sps.seq_scaling_list_8x8,
				sps.seq_scaling_list_16x16, sps.seq_scaling_list_32x32, mask,
				sps.seq_scaling_list_delta_coeff, 1)
		elif (sps.scaling_list_enable_flag):
			push(0x1000000, "hdr_38_sps_scl_dims")
			self.set_scaling_list(ctx, sl, sps.seq_scaling_list_4x4, sps.seq_scaling_list_8x8,
				sps.seq_scaling_list_16x16, sps.seq_scaling_list_32x32, mask,
				sps.seq_scaling_list_delta_coeff, 1)

	def set_refs(self, ctx, sl):
		push = self.push

		push(0x4020002, "cm3_dma_config_6")
		push(ctx.pps_tile_addrs[1] >> 8, "hdr_dc_pps_tile_addr_lsb8", 6)

		n = sl.pic.idx
		push(ctx.sps_tile_addrs[n] >> 8, "hdr_bc_sps_tile_addr_lsb8")

		push(0x70007, "cm3_dma_config_7")
		push(0x70007, "cm3_dma_config_8")
		push(0x70007, "cm3_dma_config_9")
		push(0x70007, "cm3_dma_config_a")

		pred = sl.pic.poc
		for n,pic in enumerate(ctx.dpb_list):
			if (n == 0):
				delta_base = 0
			else:
				delta_base = ctx.dpb_list[n-1].poc
			delta = delta_base - pic.poc
			pred = pred + delta
			x = ((len(ctx.dpb_list) - 1) * 0x10000000) | 0x1000000 | swrap(pred, 0x20000)
			push(x, "hdr_114_ref_hdr", n)
			push((pic.addr + ctx.rvra_offset(0)) >> 7, "hdr_134_ref0_addr_lsb7", n)
			push((pic.addr + ctx.rvra_offset(1)) >> 7, "hdr_154_ref1_addr_lsb7", n)
			push((pic.addr + ctx.rvra_offset(2)) >> 7, "hdr_174_ref2_addr_lsb7", n)
			push((pic.addr + ctx.rvra_offset(3)) >> 7, "hdr_194_ref3_addr_lsb7", n)

	def set_flags(self, ctx, sl):
		push = self.push
		sps = ctx.get_sps(sl)
		pps = ctx.get_pps(sl)
		log2_ctb_size = sps.log2_min_cb_size + sps.log2_diff_max_min_coding_block_size

		x = 0
		if (sps.pcm_enabled_flag):
			x |= 0x1000
			x |= sps.pcm_sample_bit_depth_luma_minus1 << 4
			x |= sps.pcm_sample_bit_depth_chroma_minus1 << 8
			x |= sps.log2_diff_max_min_pcm_luma_coding_block_size
		push(x, "hdr_30_sps_pcm")

		x = 0
		if (1):
			x |= set_bit(3)
		if (sps.sps_strong_intra_smoothing_enable_flag):
			x |= set_bit(9)
		push(x, "hdr_34_sps_flags")

		x = 0
		x |= (log2_ctb_size - 3) << 3
		x |= (pps.log2_parallel_merge_level - 2) << 9
		if (pps.entropy_coding_sync_enabled_flag):
			x |= set_bit(12)
		if (pps.tiles_enabled_flag):
			x |= set_bit(13)
		if (pps.transquant_bypass_enabled_flag):
			x |= set_bit(14)
		x |= ((log2_ctb_size - pps.diff_cu_qp_delta_depth - 3) & 3) << 15
		if (pps.cu_qp_delta_enabled_flag):
			x |= set_bit(17)
		if (pps.transform_skip_enabled_flag):
			x |= set_bit(18)
		if (pps.constrained_intra_pred_flag):
			x |= set_bit(19)
		if (pps.sign_data_hiding_enabled_flag):
			x |= set_bit(20)
		if ((not IS_IDR2(sl)) and self.get_cond(ctx, sl)):
			x |= set_bit(21)
		push(x, "hdr_5c_pps_flags")

		x = pps.pps_cb_qp_offset << 5 | pps.pps_cr_qp_offset
		push(x, "hdr_60_pps_qp")

		push(0, "hdr_64_zero")
		push(0, "hdr_68_zero")
		push(0, "hdr_6c_zero")
		push(0, "hdr_70_zero")
		push(0, "hdr_74_zero")
		push(0, "hdr_78_zero")

	def set_header(self, ctx, sl):
		push = self.push
		sps = ctx.get_sps(sl)
		pps = ctx.get_pps(sl)

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

		x = sps.chroma_format_idc << 24
		x |= sps.log2_diff_max_min_coding_block_size << 11
		x |= sps.log2_diff_max_min_transform_block_size << 7
		x |= sps.max_transform_hierarchy_depth_inter << 4
		x |= sps.max_transform_hierarchy_depth_intra << 1
		x |= sps.amp_enabled_flag
		push(x, "hdr_2c_sps_txfm")

		self.set_flags(ctx, sl)
		push(0x300000, "hdr_98_const_30")
		push(0x4020002, "cm3_dma_config_1")
		push(0x20002, "cm3_dma_config_2")
		push(0x0, "cm3_mark_end_section")
		# ---- FW BP -----

		push(0x4020002, "cm3_dma_config_3")
		push(0x4020002, "cm3_dma_config_4")
		push(0x0, "cm3_dma_config_4")
		push(ctx.pps_tile_addrs[0] >> 8, "hdr_dc_pps_tile_addr_lsb8", 0)
		push(ctx.pps_tile_addrs[2] >> 8, "hdr_dc_pps_tile_addr_lsb8", 1)
		push(ctx.pps_tile_addrs[3] >> 8, "hdr_dc_pps_tile_addr_lsb8", 2)
		if (pps.tiles_enabled_flag):
			push(ctx.pps_tile_addrs[4] >> 8, "hdr_dc_pps_tile_addr_lsb8", 3)
			push(ctx.pps_tile_addrs[5] >> 8, "hdr_dc_pps_tile_addr_lsb8", 4)
			push(ctx.pps_tile_addrs[6] >> 8, "hdr_dc_pps_tile_addr_lsb8", 8)
			push(ctx.pps_tile_addrs[7] >> 8, "hdr_dc_pps_tile_addr_lsb8", 9)
		else:
			push(0x0, "hdr_dc_pps_tile_addr_lsb8", 3)
			push(0x0, "hdr_dc_pps_tile_addr_lsb8", 4)
			push(ctx.pps_tile_addrs[4] >> 8, "hdr_dc_pps_tile_addr_lsb8", 8)
			push(0x0, "hdr_dc_pps_tile_addr_lsb8", 9)

		push(0x70007, "cm3_dma_config_5")
		x = sl.pic.addr
		push((x + ctx.rvra_offset(0)) >> 7, "hdr_104_curr_ref_addr_lsb7", 0)
		push((x + ctx.rvra_offset(1)) >> 7, "hdr_104_curr_ref_addr_lsb7", 1)
		push((x + ctx.rvra_offset(2)) >> 7, "hdr_104_curr_ref_addr_lsb7", 2)
		push((x + ctx.rvra_offset(3)) >> 7, "hdr_104_curr_ref_addr_lsb7", 3)
		push(0x0, "cm3_mark_end_section")

		push(ctx.y_addr >> 8, "hdr_1b4_y_addr_lsb8")
		push(round_up(ctx.width, 64) >> 4, "hdr_1bc_width_align")
		push(ctx.uv_addr >> 8, "hdr_1b8_uv_addr_lsb8")
		push(round_up(ctx.width, 64) >> 4, "hdr_1c0_width_align")
		push(0x0, "cm3_mark_end_section")
		push((((ctx.height - 1) & 0xffff) << 16) | ((ctx.width - 1) & 0xffff), "hdr_54_height_width")

		if (not IS_INTRA(sl)):
			self.set_refs(ctx, sl)

		self.set_scaling_lists(ctx, sl)

	def set_weights(self, ctx, sl):
		push = self.push
		pps = ctx.get_pps(sl)

		x = 0x2dd00000
		if (sl.has_luma_weights == 0):
			push(x, "slc_b08_cmd_weights_denom")
			return
		if ((sl.slice_type == HEVC_SLICE_P) and pps.weighted_pred_flag):
			x |= 0x40
		elif ((sl.slice_type == HEVC_SLICE_B) and (pps.weighted_bipred_flag == 1)):
			x |= 0x40
		elif ((sl.slice_type == HEVC_SLICE_B) and (pps.weighted_bipred_flag == 0)):
			x |= 0xad
		x |= (sl.luma_log2_weight_denom << 3) | sl.chroma_log2_weight_denom
		push(x, "slc_b08_cmd_weights_denom")

		num = 0
		for i in range(sl.num_ref_idx_l0_active_minus1 + 1):
			if (sl.luma_weight_l0_flag[i]):
				push(0x2de00000 | 1 << 14 | 0 << 13 | i << 9 | sl.luma_weight_l0[i], "slc_b0c_cmd_weights_weights", num)
				push(0x2df00000 | swrap(sl.luma_offset_l0[i], 0x10000), "slc_b6c_cmd_weights_offsets", num)
				num += 1
			if (sl.chroma_weight_l0_flag[i]):
				push(0x2de00000 | 2 << 14 | 0 << 13 | i << 9 | sl.chroma_weight_l0[i][0], "slc_b0c_cmd_weights_weights", num)
				push(0x2df00000 | swrap(sl.chroma_offset_l0[i][0], 0x10000), "slc_b6c_cmd_weights_offsets", num)
				num += 1
				push(0x2de00000 | 3 << 14 | 0 << 13 | i << 9 | sl.chroma_weight_l0[i][1], "slc_b0c_cmd_weights_weights", num)
				push(0x2df00000 | swrap(sl.chroma_offset_l0[i][1], 0x10000), "slc_b6c_cmd_weights_offsets", num)
				num += 1

		if (sl.slice_type == HEVC_SLICE_B):
			for i in range(sl.num_ref_idx_l1_active_minus1 + 1):
				if (sl.luma_weight_l1_flag[i]):
					push(0x2de00000 | 1 << 14 | 1 << 13 | i << 9 | sl.luma_weight_l1[i], "slc_b0c_cmd_weights_weights", num)
					push(0x2df00000 | swrap(sl.luma_offset_l1[i], 0x10000), "slc_b6c_cmd_weights_offsets", num)
					num += 1
				if (sl.chroma_weight_l1_flag[i]):
					push(0x2de00000 | 2 << 14 | 1 << 13 | i << 9 | sl.chroma_weight_l1[i][0], "slc_b0c_cmd_weights_weights", num)
					push(0x2df00000 | swrap(sl.chroma_offset_l1[i][0], 0x10000), "slc_b6c_cmd_weights_offsets", num)
					num += 1
					push(0x2de00000 | 3 << 14 | 1 << 13 | i << 9 | sl.chroma_weight_l1[i][1], "slc_b0c_cmd_weights_weights", num)
					push(0x2df00000 | swrap(sl.chroma_offset_l1[i][1], 0x10000), "slc_b6c_cmd_weights_offsets", num)
					num += 1

	def set_slice_dqtblk(self, ctx, sl):
		push = self.push
		sps = ctx.get_sps(sl)
		pps = ctx.get_pps(sl)

		x = ((26 + pps.pic_init_qp_minus26 + sl.slice_qp_delta) << 10) & 0x1fc00
		x |= swrap(pps.pps_cb_qp_offset + sl.slice_cb_qp_offset, 32) << 5
		x |= swrap(pps.pps_cr_qp_offset + sl.slice_cr_qp_offset, 32)
		push(0x2d900000 | x, "slc_bcc_cmd_quantization")

		x = 0
		x |= sl.slice_sao_chroma_flag << 6
		x |= sl.slice_sao_luma_flag << 7
		x |= swrap(sl.slice_tc_offset_div2, 16) << 8
		x |= swrap(sl.slice_beta_offset_div2, 16) << 12
		if (sps.sps_strong_intra_smoothing_enable_flag):
			x |= set_bit(16)
		if (sl.slice_loop_filter_across_slices_enabled_flag):
			x |= set_bit(17)
		if ((not pps.tiles_enabled_flag) or (pps.tiles_enabled_flag and pps.loop_filter_across_tiles_enabled_flag)):
			x |= set_bit(18)
		if (sps.pcm_enabled_flag and not sps.pcm_loop_filter_disabled_flag):
			x |= set_bit(19)
		push(0x2da00000 | x, "slc_bd0_cmd_deblocking_filter")

		if (sl.slice_type == HEVC_SLICE_P) or (sl.slice_type == HEVC_SLICE_B):
			num = 0
			for i,lst in enumerate(sl.reflist[0]):
				pos = list([x.poc for x in ctx.dpb_list]).index(lst.poc)
				push(0x2dc00000 | 0 << 8 | i << 4 | pos, "slc_a90_cmd_ref_list", i)
				num += 1
			if (sl.slice_type == HEVC_SLICE_B):
				for i,lst in enumerate(sl.reflist[1]):
					pos = list([x.poc for x in ctx.dpb_list]).index(lst.poc)
					push(0x2dc00000 | 1 << 8 | i << 4 | pos, "slc_a90_cmd_ref_list", num + i)

			self.set_weights(ctx, sl)

	def set_slice_mv(self, ctx, sl, is_dep):
		push = self.push
		cond = self.get_cond(ctx, sl)
		cond = cond and (not ctx.last_intra)
		cond = cond or sl.slice_type == HEVC_SLICE_B
		cond = cond and (not is_dep)
		cond = cond and (not sl.first_slice_segment_in_pic_flag == 0)
		#print(cond)

		x = 0
		if   (sl.slice_type == HEVC_SLICE_I):
			x |= 0x20000
		elif (sl.slice_type == HEVC_SLICE_P):
			x |= 0x10000

		if ((sl.slice_type == HEVC_SLICE_P) or (sl.slice_type == HEVC_SLICE_B)):
			x |= sl.max_num_merge_cand << 1
			if (sl.slice_type == HEVC_SLICE_B):
				if (not sl.collocated_from_l0_flag):
					x |= set_bit(4)
				if (sl.cabac_init_flag):
					x |= set_bit(5)
				if (not sl.mvd_l1_zero_flag):
					x |= set_bit(6)
				x |= sl.num_ref_idx_l1_active_minus1 << 7
			x |= sl.num_ref_idx_l0_active_minus1 << 11

			if (self.get_cond(ctx, sl) or is_dep):
				x |= set_bit(15)
			if (sl.slice_type == HEVC_SLICE_P):
				n = 0
			else:
				n = not sl.collocated_from_l0_flag
			ref = sl.reflist[n][0]
			if ((not ref.rasl) and (cond)):
				x |= set_bit(18)

		push(0x2d000000 | x, "slc_a8c_cmd_ref_type")

		if (sl.slice_type == HEVC_SLICE_P) or (sl.slice_type == HEVC_SLICE_B):
			if ((not ref.rasl) and (cond)):
				push(ctx.sps_tile_addrs[ref.idx] >> 8, "slc_bd4_sps_tile_addr2_lsb8")

	def set_coded_slice(self, sl, offset, size, t):
		push = self.push
		push(0x2d800000 | t << 13, "cm3_cmd_set_coded_slice")
		push(sl.payload_addr + offset + sl.get_payload_offset(), "slc_bd8_slice_addr")
		push(size, "slc_bdc_slice_size")
		return size

	def set_slice(self, ctx, sl, pos, c0x, has_tiles, last):
		push = self.push
		sps = ctx.get_sps(sl)
		pps = ctx.get_pps(sl)
		s = self.s

		sps.width = sps.pic_width_in_luma_samples
		sps.height = sps.pic_height_in_luma_samples
		sps.log2_ctb_size = sps.log2_min_cb_size + sps.log2_diff_max_min_coding_block_size
		sps.ctb_width  = sps.width + ((1 << sps.log2_ctb_size) - 1) >> sps.log2_ctb_size
		sps.ctb_height = (sps.height + (1 << sps.log2_ctb_size) - 1) >> sps.log2_ctb_size

		if ((pps.tiles_enabled_flag) and (sl.num_entry_point_offsets > 0)):
			size = sl.entry_point_offset[0]
		else:
			size = sl.get_payload_size()
		offset = 0
		start = offset + sl.get_payload_offset()  # hack to calc last entrypoint offset

		t = 3
		if (sl.first_slice_segment_in_pic_flag):
			t = 3
		elif (sl.dependent_slice_segment_flag and not has_tiles):
			t = 0
		elif (sl.dependent_slice_segment_flag and s.last_dep == 0):
			t = 1
		elif (not has_tiles):
			t = 2
		elif (sl.dependent_slice_segment_flag):
			t = 0
		offset += self.set_coded_slice(sl, offset, size, t)

		if (pps.tiles_enabled_flag):
			col_bd = [0] * (pps.num_tile_columns + 1)
			row_bd = [0] * (pps.num_tile_rows + 1)
			for i in range(pps.num_tile_columns):
				col_bd[i + 1] = col_bd[i] + pps.column_width[i]
			for i in range(pps.num_tile_rows):
				row_bd[i + 1] = row_bd[i] + pps.row_height[i]

		sx = pos // pps.num_tile_columns
		sy = pos % pps.num_tile_columns

		# Set top/left bound of CTB context search window
		if ((has_tiles) and (not sl.dependent_slice_segment_flag == 1)):
			rx = row_bd[sx + 0]  # Sliding window accumulator for tiles
			cy = col_bd[sy + 0]
		elif (sl.first_slice_segment_in_pic_flag == 0):
			rx = sl.slice_segment_address // sps.ctb_width
			cy = sl.slice_segment_address % sps.ctb_width
		else:
			rx = 0  # else, lower bound entire CTB
			cy = 0
		mxy = (rx & 0xffff) << 12 | cy & 0xffff  # Motion vector window resets every time

		if (sl.dependent_slice_segment_flag):
			cxy = c0x  # if it's a dependent slice, reuse the last slice's entropy window
		else:
			cxy = mxy  # else, move up
		push(0x2c000000 | cxy, "cm3_cmd_set_cabac_xy") # CABAC window

		if (sl.dependent_slice_segment_flag):
			self.set_slice_dqtblk(ctx, ctx.active_sl)
		else:
			self.set_slice_dqtblk(ctx, sl)

		# https://ieeexplore.ieee.org/document/6547985
		# "Specifically, entropy coding and reconstruction dependencies
		# are not allowed across a tile boundary. This includes motion
		# vector prediction, intra prediction and context selection"
		#
		# We make use of 4 available quadrants qx (0, 4, 8, c) to manage
		# mv/entropy/CTB context in the case tile boundaries cross slice
		# boundaries. Everything else just uses quad 0.
		#
		#  0 | 4
		#  8 | c
		#
		# Say we have,
		# sx sy r0 c0 r1 c1 qx
		#  0  0  0  0  6 13  0 | SLICE
		#  0  1  0 13  6 18  0 | tile
		#  0  2  0 18  6 22  0 | tile
		#  0  3  0 22  6 26  0 | tile
		#  0  4  0 26  6 30  0 | tile
		#  1  0  6  0 12 13  4 | tile  <- Q1; new CTB row, same context
		#
		# The hw processes in rows/cache lines, but the 6th tile occurs on the
		# CTB row below the last SLICE, we extend the current context to the
		# right (hflip) by bitwise OR 0b0100 i.e. if the the last slice was a
		# row above (and there hasn't been a slice in the same row), we | 4.
		#
		#  X x X x x  where x=0,y=4,z=8,w=c && slices are capitalized
		#  x x x X x  <- no flips yet (all x)
		#  y X x X x  <- hflip at (r2,c0) since the last slice (r0,c1) was row above
		#  y X x x X     then resets after new slice
		#  y y X x x
		#
		# The vflip (bitwise OR 0b1000) is slightly trickier.
		# A) If it's below the last slice and it's on the same column or to
		#     the right of the last slice.
		#
		# B) If it's it's below the last Q1 since the last slice and it's on
		#    the same column or to the left of the last Q1 since the last slice.
		#
		#  X x x x x
		#  y Z x x x  <- vflip even on the slice itself (c1,r1), then reset
		#  y w Z x x  <- vflip starting from c2,r2 (where above Z was), until new slice (Z)
		#  y y w Z x
		#  y y y w w
		#
		# Reset CTB context window only on tile || first slice
		cond = sl.dependent_slice_segment_flag == 1 and s.last_dep
		if ((has_tiles or sl.first_slice_segment_in_pic_flag) and not (sl.dependent_slice_segment_flag == 1 and s.last_dep)):
			s.last_dep = 1
			push(0x2a000000 | cxy, "cm3_cmd_set_ctb_xy")
			if (pps.tiles_enabled_flag):
				rx = row_bd[sx + 1] - 1
				cy = col_bd[sy + 1] - 1
				qx = 0
				# hflip doesn't apply since this is a slice itself
				if (((sy and sy >= s.last_ctx_col) and (sx > s.last_ctx_row))
				 or ((sy and sy <= s.last_q1_col) and (sx > s.last_q1_row))):
					qx |= 8  # vflip
				s.last_ctx_row = sx
				s.last_ctx_col = sy
				s.last_q1_row = -1  # null Q1 on slice
				s.last_q1_col = -1
			else:
				rx = sps.ctb_height - 1
				cy = sps.ctb_width - 1
				qx = 0  # quad 0
			push(qx << 28 | sy << 24 | (rx & 0xffff) << 12 | cy & 0xffff, "cm3_set_ctb_xy")
		else:
			s.last_dep = 0
		if (not cond):
			pos += 1

		if (sl.dependent_slice_segment_flag):
			self.set_slice_mv(ctx, ctx.active_sl, 1)
		else:
			self.set_slice_mv(ctx, sl, 0)
		# Unlike entropy, motion vector window resets every time
		# Not sure why their firmware uses column 1 for mv though; obv doesn't
		# affect decode
		push(0 << 28 | 1 << 24 | mxy, "cm3_set_mv_xy")

		# Repeat for tiles/entry points. This should actually be a single loop
		# contiuning from above, but things are bad as it is
		if ((pps.tiles_enabled_flag) and (sl.num_entry_point_offsets > 0)):
			for n in range(sl.num_entry_point_offsets + 1 - 1):  # We did tile #0 above
				push(0x2b000000, "cm3_cmd_inst_fifo_start")
				if (n != sl.num_entry_point_offsets - 1):
					size = sl.entry_point_offset[n + 1]
				else:
					size = sl.get_payload_total_size() - offset - start
				offset += self.set_coded_slice(sl, offset, size, 1)

				sx = pos // pps.num_tile_columns
				sy = pos % pps.num_tile_columns
				mxy = (row_bd[sx] & 0xffff) << 12 | col_bd[sy] & 0xffff
				xy = ((row_bd[sx + 1] - 1) & 0xffff) << 12 | (col_bd[sy + 1] - 1) & 0xffff

				qx = 0
				# vflip:
				if (((sy and sy >= s.last_ctx_col) and (sx > s.last_ctx_row))
				 or ((sy and sy <= s.last_q1_col) and (sx > s.last_q1_row))):
					qx |= 8
				# hflip: If the last slice was a row above
				if (sx and (sx == (s.last_ctx_row + 1))):
					qx |= 4
					if (qx == 4):
						s.last_q1_row = sx  # save Q1 position
						s.last_q1_col = sy
				# tiles are mututally exclusive with dependent slice, so cxy == mxy
				push(0x2a000000 | mxy, "cm3_cmd_set_tile_ctb_xy")
				push(qx << 28 | sy << 24 | xy, "cm3_set_tile_ctb_xy")
				push(0 << 28 | 1 << 24 | mxy, "cm3_set_tile_mv_xy")
				pos += 1

		push(0x2b000000 | boolify(last) << 10, "cm3_cmd_inst_fifo_end")
		return pos, cxy

	def set_slices(self, ctx, sl):
		sps = ctx.get_sps(sl)
		pps = ctx.get_pps(sl)
		self.s = dotdict()  # mini context for convenience
		self.s.last_q1_row = -1
		self.s.last_q1_col = -1
		self.s.last_dep = 0

		has_tiles = 0
		if ((sl.first_slice_segment_in_pic_flag) and len(sl.slices)):
			for i,s in enumerate(sl.slices):
				has_tiles |= s.pps.tiles_enabled_flag

		count = len(sl.slices)
		pos = 0
		c0x = -1
		pos, c0x = self.set_slice(ctx, sl, pos, c0x, has_tiles, last=count == 0)
		count -= 1
		if ((sl.first_slice_segment_in_pic_flag) and len(sl.slices)):
			for i,s in enumerate(sl.slices):
				pos, c0x = self.set_slice(ctx, s, pos, c0x, has_tiles, last=count == 0)
				count -= 1
		ctx.pos = pos  # For driver-side submission (need decode command for every slice+tile)

	def set_insn(self, ctx, sl):
		self.set_header(ctx, sl)
		self.set_slices(ctx, sl)
