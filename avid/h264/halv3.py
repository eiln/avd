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

	def get_pps(self, ctx, sl):
		return ctx.pps_list[sl.pic_parameter_set_id]

	def get_sps(self, ctx, sl):
		return ctx.sps_list[self.get_pps(ctx, sl).seq_parameter_set_id]

	def get_sps_tile_iova(self, ctx, n):
		return ctx.sps_tile_addr + (ctx.sps_tile_size * (n % ctx.sps_tile_count))

	def rvra_offset(self, ctx, idx):
		if   (idx == 0): return ctx.rvra_size0
		elif (idx == 1): return 0
		elif (idx == 2): return ctx.rvra_size0 + ctx.rvra_size1 + ctx.rvra_size2
		elif (idx == 3): return ctx.rvra_size0 + ctx.rvra_size1
		raise ValueError("invalid rvra group (%d)" % idx)

	def set_refs(self, ctx, sl):
		avd_set = self.avd_set

		avd_set(0x4020002, "fw_dma_config_6")
		avd_set((ctx.pps_tile_addr + (ctx.pps_tile_size * 4)) >> 8, "pps_tile_addr")
		avd_set(self.get_sps_tile_iova(ctx, ctx.access_idx) >> 8, "hdr_bc_sps_tile_addr_lsb8")

		avd_set(0x70007, "fw_dma_config_7")
		avd_set(0x70007, "fw_dma_config_8")
		avd_set(0x70007, "fw_dma_config_9")
		avd_set(0x70007, "fw_dma_config_a")

		pred = sl.pic.poc
		for n,rvra in enumerate(ctx.dpb_list):
			if (n == 0):
				delta_base = 0
			else:
				delta_base = ctx.dpb_list[n-1].poc
			delta = delta_base - rvra.poc
			pred = pred + delta
			x = ((len(ctx.dpb_list) - 1) * 0x10000000) | 0x1000000 | swrap(pred, 0x20000)
			avd_set(x, "hdr_d0_ref_hdr", n)
			avd_set((rvra.addr + self.rvra_offset(ctx, 0)) >> 7, "hdr_110_ref0_addr_lsb7", n)
			avd_set((rvra.addr + self.rvra_offset(ctx, 1)) >> 7, "hdr_150_ref1_addr_lsb7", n)
			avd_set((rvra.addr + self.rvra_offset(ctx, 2)) >> 7, "hdr_190_ref2_addr_lsb7", n)
			avd_set((rvra.addr + self.rvra_offset(ctx, 3)) >> 7, "hdr_1d0_ref3_addr_lsb7", n)

	def set_header(self, ctx, sl):
		avd_set = self.avd_set

		assert((ctx.inst_fifo_idx >= 0) and (ctx.inst_fifo_idx <= ctx.inst_fifo_count))
		avd_set(0x2b000100 + (ctx.inst_fifo_idx * 0x10), "fw_cmd_inst_fifo_start")
		#print("x: 0x%x y: 0x%x" % (avd_r32(0x1104020), avd_r32(0x1104034))) FW BP

		x = 0x2db012e0
		if (sl.nal_unit_type == H264_NAL_SLICE_IDR):
			x |= 0x2000
		avd_set(x, "hdr_34_cmd_start_hdr")

		avd_set(0x1000000, "hdr_38_pixfmt")
		avd_set((((ctx.height - 1) & 0xffff) << 16) | ((ctx.width - 1) & 0xffff), "hdr_3c_height_width")
		avd_set(0x0, "fw_dma_config_0")
		avd_set((((ctx.height - 1) >> 3) << 16) | ((ctx.width - 1) >> 3), "hdr_28_height_width_shift3")
		avd_set(0x1002881, "hdr_2c_sps_param")

		x = 0x100000
		if (sl.nal_unit_type != H264_NAL_SLICE_IDR):
			x |= 0x200000
		avd_set(x, "hdr_44_is_idr_mask")

		avd_set(0x3de, "hdr_48_3de")
		avd_set(0x30000a, "hdr_58_const_3a")
		avd_set(0x4020002, "fw_dma_config_1")
		avd_set(0x20002, "fw_dma_config_2")
		avd_set(0x0)
		avd_set((ctx.pps_tile_addr + (ctx.pps_tile_size * 0)) >> 8, "hdr_9c_pps_tile_addr_lsb8", 0)
		#print("x: 0x%x y: 0x%x" % (avd_r32(0x1104020), avd_r32(0x1104034))) FW BP

		avd_set(0x4020002, "fw_dma_config_3")
		avd_set(0x4020002, "fw_dma_config_4")
		avd_set(0x0)
		avd_set((ctx.pps_tile_addr + (ctx.pps_tile_size * 1)) >> 8, "hdr_9c_pps_tile_addr_lsb8", 1)
		avd_set((ctx.pps_tile_addr + (ctx.pps_tile_size * 2)) >> 8, "hdr_9c_pps_tile_addr_lsb8", 2)
		avd_set((ctx.pps_tile_addr + (ctx.pps_tile_size * 3)) >> 8, "hdr_9c_pps_tile_addr_lsb8", 3)
		avd_set(0x70007, "fw_dma_config_5")

		avd_set((sl.pic.addr + self.rvra_offset(ctx, 0)) >> 7, "hdr_c0_curr_ref_addr_lsb7", 0)
		avd_set((sl.pic.addr + self.rvra_offset(ctx, 1)) >> 7, "hdr_c0_curr_ref_addr_lsb7", 1)
		avd_set((sl.pic.addr + self.rvra_offset(ctx, 2)) >> 7, "hdr_c0_curr_ref_addr_lsb7", 2)
		avd_set((sl.pic.addr + self.rvra_offset(ctx, 3)) >> 7, "hdr_c0_curr_ref_addr_lsb7", 3)

		avd_set(ctx.y_addr >> 8, "hdr_210_y_addr_lsb8")
		avd_set((round_up(ctx.width, 64) >> 6) << 2, "hdr_218_width_align")
		avd_set(ctx.uv_addr >> 8, "hdr_214_uv_addr_lsb8")
		avd_set((round_up(ctx.width, 64) >> 6) << 2, "hdr_21c_width_align")
		avd_set(0x0)
		avd_set((((ctx.height - 1) & 0xffff) << 16) | ((ctx.width - 1) & 0xffff), "hdr_54_height_width")

		if (sl.nal_unit_type != H264_NAL_SLICE_IDR):
			self.set_refs(ctx, sl)

		avd_set(0x0)
		#print("x: 0x%x y: 0x%x" % (avd_r32(0x1104020), avd_r32(0x1104034))) FW BP

	def set_weights(self, ctx, sl):
		avd_set = self.avd_set

		if (sl.slice_type == H264_SLICE_TYPE_P):
			x = 0x2dd00040
		else:
			x = 0x2dd000ad
		if (sl.has_luma_weights == 0):
			avd_set(x, "slc_76c_cmd_mb")
			return
		x |= (sl.luma_log2_weight_denom << 3) | sl.chroma_log2_weight_denom
		avd_set(x, "slc_76c_cmd_mb")

		def get_wbase(i, j): return 0x2de00000 | ((j + 1) * 0x4000) | (i * 0x200)
		num = 0
		for i in range(sl.num_ref_idx_l0_active_minus1 + 1):
			if (sl.luma_weight_l0_flag[i]):
				avd_set(get_wbase(i, 0) | sl.luma_weight_l0[i], "slc_770_cmd_weights_weights", num)
				avd_set(0x2df00000 | swrap(sl.luma_offset_l0[i], 0x10000), "slc_8f0_cmd_weights_offsets", num)
				num += 1
			if (sl.chroma_weight_l0_flag[i]):
				avd_set(get_wbase(i, 1) | sl.chroma_weight_l0[i][0], "slc_770_cmd_weights_weights", num)
				avd_set(0x2df00000 | swrap(sl.chroma_offset_l0[i][0], 0x10000), "slc_8f0_cmd_weights_offsets", num)
				num += 1
				avd_set(get_wbase(i, 2) | sl.chroma_weight_l0[i][1], "slc_770_cmd_weights_weights", num)
				avd_set(0x2df00000 | swrap(sl.chroma_offset_l0[i][1], 0x10000), "slc_8f0_cmd_weights_offsets", num)
				num += 1

		if (sl.slice_type == H264_SLICE_TYPE_B):
			for i in range(sl.num_ref_idx_l1_active_minus1 + 1):
				if (sl.luma_weight_l1_flag[i]):
					avd_set(get_wbase(i, 0) | sl.luma_weight_l1[i], "slc_770_cmd_weights_weights", num)
					avd_set(0x2df00000 | swrap(sl.luma_offset_l1[i], 0x10000), "slc_8f0_cmd_weights_offsets", num)
					num += 1
				if (sl.chroma_weight_l1_flag[i]):
					avd_set(get_wbase(i, 1) | sl.chroma_weight_l1[i][0], "slc_770_cmd_weights_weights", num)
					avd_set(0x2df00000 | swrap(sl.chroma_offset_l1[i][0], 0x10000), "slc_8f0_cmd_weights_offsets", num)
					num += 1
					avd_set(get_wbase(i, 2) | sl.chroma_weight_l1[i][1], num)
					avd_set(0x2df00000 | swrap(sl.chroma_offset_l1[i][1], 0x10000), "slc_8f0_cmd_weights_offsets", num)
					num += 1

	def set_slice(self, ctx, sl):
		avd_set = self.avd_set
		avd_set(0x2d800000, "slc_a7c_cmd_d8")
		avd_set(ctx.slice_data_addr + sl.get_payload_offset(), "inp_8b4d4_slice_addr_low")
		avd_set(sl.get_payload_size(), "inp_8b4d8_slice_hdr_size")
		avd_set(0x2c000000)
		#print("x: 0x%x y: 0x%x" % (avd_r32(0x1104020), avd_r32(0x1104034))) FW BP

		avd_set(0x2d900000 | ((26 + self.get_pps(ctx, sl).pic_init_qp_minus26 + sl.slice_qp_delta) * 0x400), "slc_a70_cmd_slice_qpy")
		avd_set(0x2da30000, "slc_a74_cmd_a3")

		if (sl.slice_type == H264_SLICE_TYPE_P) or (sl.slice_type == H264_SLICE_TYPE_B):
			lx = 0
			for i,lst in enumerate(sl.pic.list0):
				pos = list([x.pic_num for x in ctx.dpb_list]).index(lst.pic_num)
				avd_set(0x2dc00000 | (lx << 8) | (i << 4) | pos, "slc_6e8_cmd_ref_list_0", i)
			if (sl.slice_type == H264_SLICE_TYPE_B):
				lx = 1
				for i,lst in enumerate(sl.pic.list1):
					pos = list([x.pic_num for x in ctx.dpb_list]).index(lst.pic_num)
					avd_set(0x2dc00000 | (lx << 8) | (i << 4) | pos,
					"slc_6e8_cmd_ref_list_0", i + len(sl.pic.list0))

			self.set_weights(ctx, sl)

		avd_set(0x2a000000)
		avd_set((((ctx.height - 1) >> 4) << 12) | ((ctx.width - 1) >> 4), "fw_height_width_shift_4")

		x = 0x2d000000
		if   (sl.slice_type == H264_SLICE_TYPE_I):
			x |= 0x20000
		elif (sl.slice_type == H264_SLICE_TYPE_P):
			x |= 0x10000
		elif (sl.slice_type == H264_SLICE_TYPE_B):
			x |= 0x40000

		if ((sl.slice_type == H264_SLICE_TYPE_P) or (sl.slice_type == H264_SLICE_TYPE_B)):
			if (sl.num_ref_idx_active_override_flag != 0):
				x |= sl.num_ref_idx_l0_active_minus1 << 11
				if (sl.slice_type == H264_SLICE_TYPE_B):
					x |= sl.num_ref_idx_l1_active_minus1 << 7
			else:
				x |= 0x1000
		avd_set(x, "slc_6e4_cmd_ref_type")

		if (sl.slice_type == H264_SLICE_TYPE_B):
			n = ctx.last_p_sps_tile_idx + sl.num_ref_idx_l1_active_minus1
			avd_set(self.get_sps_tile_iova(ctx, n) >> 8, "sps_tile_addr_b")

		avd_set(0x2b000400, "fw_cmd_inst_fifo_end")

	def set_insn(self, ctx, sl):
		self.set_header(ctx, sl)
		self.set_slice(ctx, sl)
