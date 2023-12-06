#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..hal import AVDHal
from ..utils import *
from .types import *

class AVDH264HalV3(AVDHal):
	def __init__(self):
		super().__init__()

	# The idea is to pass the HALs a RO struct parsed/managed by AVDH264Decoder

	def set_refs(self, ctx, sl):
		push = self.push

		push(0x4020002, "cm3_dma_config_6")
		push(ctx.pps_tile_addrs[4] >> 8, "hdr_9c_pps_tile_addr_lsb8", 7)
		push(ctx.sps_tile_addrs[sl.pic.sps_idx] >> 8, "hdr_bc_sps_tile_addr_lsb8")

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
			x = (len(ctx.dpb_list) - 1) << 28 | 0x1000000
			x |= boolify(pic.flags & H264_FRAME_FLAG_LONG_REF) << 17 | swrap(pred, 1 << 17)
			push(x, "hdr_d0_ref_hdr", n)
			push((pic.addr + ctx.rvra_offset(0)) >> 7, "hdr_110_ref0_addr_lsb7", n)
			push((pic.addr + ctx.rvra_offset(1)) >> 7, "hdr_150_ref1_addr_lsb7", n)
			push((pic.addr + ctx.rvra_offset(2)) >> 7, "hdr_190_ref2_addr_lsb7", n)
			push((pic.addr + ctx.rvra_offset(3)) >> 7, "hdr_1d0_ref3_addr_lsb7", n)

	def set_scaling_list(self, ctx, sl):
		push = self.push
		sps = ctx.get_sps(sl)
		pps = ctx.get_pps(sl)

		x = 0
		if (pps.pic_scaling_matrix_present_flag or sps.seq_scaling_matrix_present_flag):
			x |= 0x1000000
		else:
			push(x, "cm3_mark_end_section_scl")
			return

		# SPS: Set iff explicitly decoded non-default scaling list
		# mask aggregates all flags in u16; flag cleared if default for SPS
		if (sps.seq_scaling_matrix_present_flag and sps.seq_scaling_matrix_present_mask):
			x |= ((64 // 4) << 5) | ((16 // 4) << 5) - 1
		if (sps.seq_scaling_matrix_present_flag):
			push(x, "hdr_30_seq_scaling_list_dims")

		if (sps.seq_scaling_matrix_present_flag and sps.seq_scaling_matrix_present_mask):
			for i in range(6):
				if (sps.seq_scaling_list_present_flag[i]): # Do not set default list
					for j in range(16 // 4):
						y = j * 4
						x = 0
						x |= sps.seq_scaling_list_4x4[i][y + 0] << 24
						x |= sps.seq_scaling_list_4x4[i][y + 1] << 16
						x |= sps.seq_scaling_list_4x4[i][y + 2] << 8
						x |= sps.seq_scaling_list_4x4[i][y + 3] << 0
						push(x, "scl_28c_seq_scaling_matrix_4x4", i*(16 // 4) + j)

			for i in range(6):
				if (sps.seq_scaling_list_present_flag[i + 6]):
					for j in range(64 // 4):
						y = j * 4
						x = 0
						x |= sps.seq_scaling_list_8x8[i][y + 0] << 24
						x |= sps.seq_scaling_list_8x8[i][y + 1] << 16
						x |= sps.seq_scaling_list_8x8[i][y + 2] << 8
						x |= sps.seq_scaling_list_8x8[i][y + 3] << 0
						push(x, "scl_2ec_seq_scaling_matrix_8x8", i*(64 // 4) + j)

		# TODO unsure of this order; I've yet to see both SPS/PPS
		# PPS: Set all lists unconditionally if flag is present
		if (pps.pic_scaling_matrix_present_flag):
			x |= ((64 // 4) << 5) | ((16 // 4) << 5) - 1
			push(x, "hdr_4c_pic_scaling_list_dims")

		if (pps.pic_scaling_matrix_present_flag):
			for i in range(6):
				for j in range(16 // 4): # Set unconditionally
					y = j * 4
					x = 0
					x |= pps.pic_scaling_list_4x4[i][y + 0] << 24
					x |= pps.pic_scaling_list_4x4[i][y + 1] << 16
					x |= pps.pic_scaling_list_4x4[i][y + 2] << 8
					x |= pps.pic_scaling_list_4x4[i][y + 3] << 0
					push(x, "scl_46c_pic_scaling_matrix_4x4", i*(16 // 4) + j)

			if (pps.transform_8x8_mode_flag):
				for i in range(6):
					if (pps.pic_scaling_list_present_flag[i + 6]):
						for j in range(64 // 4):
							y = j * 4
							x = 0
							x |= pps.pic_scaling_list_8x8[i][y + 0] << 24
							x |= pps.pic_scaling_list_8x8[i][y + 1] << 16
							x |= pps.pic_scaling_list_8x8[i][y + 2] << 8
							x |= pps.pic_scaling_list_8x8[i][y + 3] << 0
							push(x, "scl_4cc_pic_scaling_matrix_8x8", i*(64 // 4) + j)
			else:
				default_8x8_intra_scaling_list = [
					0x060a0d10, 0x0a0b1012, 0x0d101217, 0x10121719,
					0x1217191b, 0x17191b1d, 0x191b1d1f, 0x1b1d1f21,
					0x1217191b, 0x17191b1d, 0x191b1d1f, 0x1b1d1f21,
					0x1d1f2124, 0x1f212426, 0x21242628, 0x2426282a,
				]
				default_8x8_inter_scaling_list = [
					0x090d0f11, 0x0d0d1113, 0x0f111315, 0x11131516,
					0x13151618, 0x15161819, 0x1618191b, 0x18191b1c,
					0x13151618, 0x15161819, 0x1618191b, 0x18191b1c,
					0x191b1c1e, 0x1b1c1e20, 0x1c1e2021, 0x1e202123,
				]
				for i in range(len(default_8x8_intra_scaling_list)):
					push(default_8x8_intra_scaling_list[i], "scl_4cc_pic_scaling_matrix_8x8", i)
				for i in range(len(default_8x8_inter_scaling_list)):
					push(default_8x8_inter_scaling_list[i], "scl_4cc_pic_scaling_matrix_8x8", i)

	def set_header(self, ctx, sl):
		push = self.push
		sps = ctx.get_sps(sl)
		pps = ctx.get_pps(sl)

		assert((ctx.inst_fifo_idx >= 0) and (ctx.inst_fifo_idx <= ctx.inst_fifo_count))
		push(0x2b000000 | 0x100 | (ctx.inst_fifo_idx * 0x10), "cm3_cmd_inst_fifo_start")
		# ---- FW BP -----

		x = 0x1000
		if (sl.nal_unit_type == H264_NAL_SLICE_IDR):
			x |= 0x2000
		x |= 0x2e0
		push(0x2db00000 | x, "hdr_34_cmd_start_hdr")

		push(0x1000000, "hdr_38_mode")
		push((((ctx.height - 1) & 0xffff) << 16) | ((ctx.width - 1) & 0xffff), "hdr_3c_height_width")
		push(0x0, "hdr_40_zero")
		push((((ctx.height - 1) >> 3) << 16) | ((ctx.width - 1) >> 3), "hdr_28_height_width_shift3")

		x = 0x1000000 * sps.chroma_format_idc | 0x2000 | 0x800
		x |= (pps.transform_8x8_mode_flag << 7)  # 4x4, 8x8
		x |= sps.direct_8x8_inference_flag
		push(x, "hdr_2c_sps_param")

		x = 0
		if (pps.entropy_coding_mode_flag):
			x |= set_bit(20)
		if (sl.nal_unit_type != H264_NAL_SLICE_IDR):
			x |= set_bit(21)
		push(x, "hdr_44_flags")

		x = swrap(pps.chroma_qp_index_offset, 32) << 5 | swrap(pps.second_chroma_qp_index_offset, 32)
		push(x, "hdr_48_chroma_qp_index_offset")
		push(0x30000a, "hdr_58_const_3a")
		push(0x4020002, "cm3_dma_config_1")
		push(0x20002, "cm3_dma_config_2")
		push(0x0, "cm3_mark_end_section")
		push(ctx.pps_tile_addrs[0] >> 8, "hdr_9c_pps_tile_addr_lsb8", 0)
		# ---- FW BP -----

		push(0x4020002, "cm3_dma_config_3")
		push(0x4020002, "cm3_dma_config_4")
		push(0x0, "cm3_mark_end_section")
		push(ctx.pps_tile_addrs[1] >> 8, "hdr_9c_pps_tile_addr_lsb8", 1)
		push(ctx.pps_tile_addrs[2] >> 8, "hdr_9c_pps_tile_addr_lsb8", 2)
		push(ctx.pps_tile_addrs[3] >> 8, "hdr_9c_pps_tile_addr_lsb8", 3)
		push(0x70007, "cm3_dma_config_5")

		push((sl.pic.addr + ctx.rvra_offset(0)) >> 7, "hdr_c0_curr_ref_addr_lsb7", 0)
		push((sl.pic.addr + ctx.rvra_offset(1)) >> 7, "hdr_c0_curr_ref_addr_lsb7", 1)
		push((sl.pic.addr + ctx.rvra_offset(2)) >> 7, "hdr_c0_curr_ref_addr_lsb7", 2)
		push((sl.pic.addr + ctx.rvra_offset(3)) >> 7, "hdr_c0_curr_ref_addr_lsb7", 3)

		push(ctx.y_addr >> 8, "hdr_210_y_addr_lsb8")
		push(round_up(ctx.width, 64) >> 4, "hdr_218_width_align")
		push(ctx.uv_addr >> 8, "hdr_214_uv_addr_lsb8")
		push(round_up(ctx.width, 64) >> 4, "hdr_21c_width_align")
		push(0x0, "cm3_mark_end_section")
		push((((ctx.height - 1) & 0xffff) << 16) | ((ctx.width - 1) & 0xffff), "hdr_54_height_width")

		if (sl.nal_unit_type != H264_NAL_SLICE_IDR):
			self.set_refs(ctx, sl)

		self.set_scaling_list(ctx, sl)
		# ---- FW BP -----

	def set_weights(self, ctx, sl):
		push = self.push
		pps = ctx.get_pps(sl)

		x = 0x2dd00000
		if ((sl.slice_type == H264_SLICE_TYPE_P) and pps.weighted_pred_flag):
			x |= 0x40
		elif ((sl.slice_type == H264_SLICE_TYPE_B) and (pps.weighted_bipred_idc == 1)):
			x |= 0xad
		else:
			if ((sl.slice_type == H264_SLICE_TYPE_B) and (pps.weighted_bipred_idc == 2)):
				x |= 0xad
			push(x, "slc_76c_cmd_weights_denom")
			return
		x |= (sl.luma_log2_weight_denom << 3) | sl.chroma_log2_weight_denom
		push(x, "slc_76c_cmd_weights_denom")

		num = 0
		for i in range(sl.num_ref_idx_l0_active_minus1 + 1):
			if (sl.luma_weight_l0_flag[i]):
				push(0x2de00000 | 1 << 14 | i << 9 | sl.luma_weight_l0[i], "slc_770_cmd_weights_weights", num)
				push(0x2df00000 | swrap(sl.luma_offset_l0[i], 0x10000), "slc_8f0_cmd_weights_offsets", num)
				num += 1
			if (sl.chroma_weight_l0_flag[i]):
				push(0x2de00000 | 2 << 14 | i << 9 | sl.chroma_weight_l0[i][0], "slc_770_cmd_weights_weights", num)
				push(0x2df00000 | swrap(sl.chroma_offset_l0[i][0], 0x10000), "slc_8f0_cmd_weights_offsets", num)
				num += 1
				push(0x2de00000 | 3 << 14 | i << 9 | sl.chroma_weight_l0[i][1], "slc_770_cmd_weights_weights", num)
				push(0x2df00000 | swrap(sl.chroma_offset_l0[i][1], 0x10000), "slc_8f0_cmd_weights_offsets", num)
				num += 1

		if (sl.slice_type == H264_SLICE_TYPE_B):
			for i in range(sl.num_ref_idx_l1_active_minus1 + 1):
				if (sl.luma_weight_l1_flag[i]):
					push(0x2de00000 | 1 << 14 | i << 9 | sl.luma_weight_l1[i], "slc_770_cmd_weights_weights", num)
					push(0x2df00000 | swrap(sl.luma_offset_l1[i], 0x10000), "slc_8f0_cmd_weights_offsets", num)
					num += 1
				if (sl.chroma_weight_l1_flag[i]):
					push(0x2de00000 | 2 << 14 | i << 9 | sl.chroma_weight_l1[i][0], "slc_770_cmd_weights_weights", num)
					push(0x2df00000 | swrap(sl.chroma_offset_l1[i][0], 0x10000), "slc_8f0_cmd_weights_offsets", num)
					num += 1
					push(0x2de00000 | 3 << 14 | i << 9 | sl.chroma_weight_l1[i][1], num)
					push(0x2df00000 | swrap(sl.chroma_offset_l1[i][1], 0x10000), "slc_8f0_cmd_weights_offsets", num)
					num += 1

	def set_slice(self, ctx, sl):
		push = self.push
		pps = ctx.get_pps(sl)

		x = 0  # CABAC we skipped cabac_alignment_bit
		if (pps.entropy_coding_mode_flag == 0): # CAVLC we didn't
			x = sl.slice_header_size % 8
		push(0x2d800000 | x << 15, "slc_a7c_cmd_set_coded_slice")
		push(ctx.slice_data_addr + sl.get_payload_offset(), "slc_a84_slice_addr_low")
		push(sl.get_payload_size(), "slc_a88_slice_hdr_size")
		push(0x2c000000, "cm3_cmd_exec_mb_vp")
		# ---- FW BP -----

		push(0x2d900000 | ((26 + pps.pic_init_qp_minus26 + sl.slice_qp_delta) * 0x400), "slc_a70_cmd_quant_param")

		x = 0
		if (sl.disable_deblocking_filter_idc == 0):
			x |= set_bit(17)
		if (sl.disable_deblocking_filter_idc != 1):
			x |= set_bit(16)
			x |= swrap(sl.slice_beta_offset_div2, 16) << 12
			x |= swrap(sl.slice_alpha_c0_offset_div2, 16) << 8
		push(0x2da00000 | x, "slc_a74_cmd_deblocking_filter")

		if (sl.slice_type == H264_SLICE_TYPE_P) or (sl.slice_type == H264_SLICE_TYPE_B):
			for i,pic in enumerate(sl.list0):
				pos = list([x.pic_num for x in ctx.dpb_list]).index(pic.pic_num)
				push(0x2dc00000 | 0 << 8 | i << 4 | pos, "slc_6e8_cmd_ref_list_0", i)
			if (sl.slice_type == H264_SLICE_TYPE_B):
				for i,pic in enumerate(sl.list1):
					pos = list([x.pic_num for x in ctx.dpb_list]).index(pic.pic_num)
					push(0x2dc00000 | 1 << 8 | i << 4 | pos,
					"slc_6e8_cmd_ref_list_0", i + len(sl.list0))

			self.set_weights(ctx, sl)

		push(0x2a000000, "cm3_cmd_set_mb_dims")
		push((((ctx.height - 1) >> 4) << 12) | ((ctx.width - 1) >> 4), "cm3_set_mb_dims")

		x = 0x2d000000
		if   (sl.slice_type == H264_SLICE_TYPE_I):
			x |= 0x20000
		elif (sl.slice_type == H264_SLICE_TYPE_P):
			x |= 0x10000
		elif (sl.slice_type == H264_SLICE_TYPE_B):
			x |= 0x40000
		if ((sl.slice_type == H264_SLICE_TYPE_P) or (sl.slice_type == H264_SLICE_TYPE_B)):
			x |= sl.num_ref_idx_l0_active_minus1 << 11
			if (sl.slice_type == H264_SLICE_TYPE_B):
				x |= sl.num_ref_idx_l1_active_minus1 << 7
				if (not sl.direct_spatial_mb_pred_flag):
					x |= 16 << 11
			if (pps.entropy_coding_mode_flag):
				x |= sl.cabac_init_idc << 5
		push(x, "slc_6e4_cmd_ref_type")

		if (sl.slice_type == H264_SLICE_TYPE_B):
			# bidirectional reference of previous mv
			push(ctx.sps_tile_addrs[sl.list1[0].sps_idx] >> 8, "slc_a78_sps_tile_addr2_lsb8")

		push(0x2b000000 | 0x400, "cm3_cmd_inst_fifo_end")

	def set_insn(self, ctx, sl):
		self.set_header(ctx, sl)
		self.set_slice(ctx, sl)
