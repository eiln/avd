#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..decoder import AVDDecoder, AVDOutputFormat
from ..utils import *
from .fp import AVDH264V3FrameParams
from .halv3 import AVDH264HalV3
from .parser import AVDH264Parser
from .rlm import AVDH264RLM, AVDH264Picture
from .types import *
from math import sqrt

class AVDH264Ctx(dotdict):
	def get_pps(self, sl):
		return self.pps_list[sl.pic_parameter_set_id]

	def get_sps(self, sl):
		return self.sps_list[self.get_pps(sl).seq_parameter_set_id]

	def rvra_offset(self, idx):
		if   (idx == 0): return self.rvra_size0
		elif (idx == 1): return 0
		elif (idx == 2): return self.rvra_size0 + self.rvra_size1 + self.rvra_size2
		elif (idx == 3): return self.rvra_size0 + self.rvra_size1
		raise ValueError("invalid rvra group (%d)" % idx)

class AVDH264Decoder(AVDDecoder):
	def __init__(self):
		super().__init__(AVDH264Parser, AVDH264HalV3, AVDH264V3FrameParams)
		self.mode = "h264"
		self.rlm = AVDH264RLM(self)

	def new_context(self, sps_list, pps_list):
		self.ctx = AVDH264Ctx()
		ctx = self.ctx
		ctx.sps_list = sps_list
		ctx.pps_list = pps_list

		ctx.access_idx = 0
		ctx.width = -1
		ctx.height = -1
		ctx.active_sl = None
		ctx.cur_sps_id = -1

		ctx.prev_poc_lsb = 0
		ctx.prev_poc_msb = 0
		ctx.max_lt_idx = -1
		ctx.dpb_list = []
		ctx.dpb_pool = []
		self.rlm.ctx = ctx

	def setup(self, path, num=0, nal_stop=0, **kwargs):
		sps_list, pps_list, slices = self.parser.parse(path, num, nal_stop, **kwargs)
		self.new_context(sps_list, pps_list)
		return slices

	def refresh_sps(self, sl):
		ctx = self.ctx
		pps = ctx.get_pps(sl)
		sps_id = pps.seq_parameter_set_id
		if (sps_id == ctx.cur_sps_id):
			return
		sps = ctx.sps_list[sps_id]

		width = ((sps.pic_width_in_mbs_minus1 + 1) * 16) - (sps.frame_crop_right_offset * 2) - (sps.frame_crop_left_offset * 2)
		height = ((2 - sps.frame_mbs_only_flag) * (sps.pic_height_in_map_units_minus1 + 1) * 16) - (sps.frame_crop_bottom_offset * 2) - (sps.frame_crop_top_offset * 2)

		ctx.orig_width = width
		ctx.orig_height = height
		if (width & 15):
			width = round_up(width, 16)
		if (height & 15):
			height = round_up(height, 16)
		if ((width != ctx.orig_width) or (height != ctx.orig_height)):
			self.log("dimensions changed from %dx%d -> %dx%d" % (ctx.width, ctx.height, width, height))
		ctx.width = width
		ctx.height = height

		# Hardware caps
		assert((64 <= width and width <= 4096) and (64 <= height and height <= 4096))
		assert(not(width & 15) and not(height & 15))
		assert((sps.chroma_format_idc == H264_CHROMA_IDC_420) or
		       (sps.chroma_format_idc == H264_CHROMA_IDC_422))
		if (sps.bit_depth_luma_minus8 != sps.bit_depth_chroma_minus8):
			raise ValueError("Haven't tested")

		stride = round_up(sps.bit_depth_luma_minus8 + 8, 8) // 8
		ctx.fmt = AVDOutputFormat(
			in_width         = ((round_up(ctx.width * stride, 64) >> 4) << 4),
			in_height        = (round_up(ctx.height, 16) >> 4) << 4,
			out_width        = ctx.orig_width,
			out_height       = ctx.orig_height,
			chroma           = sps.chroma_format_idc,
			bitdepth_luma    = sps.bit_depth_luma_minus8 + 8,
			bitdepth_chroma  = sps.bit_depth_chroma_minus8 + 8,
		)
		ctx.fmt.x0 = 0
		ctx.fmt.x1 = ctx.fmt.out_width  # TODO vui frame crop
		ctx.fmt.y0 = 0
		ctx.fmt.y1 = ctx.fmt.out_height
		self.log(ctx.fmt)
		assert(ctx.fmt.in_width >= ctx.fmt.out_width)
		assert(ctx.fmt.in_height >= ctx.fmt.out_height)

		ctx.max_frame_num = 1 << (sps.log2_max_frame_num_minus4 + 4)
		if (sps.vui_parameters_present_flag):
			ctx.num_reorder_frames = sps.num_reorder_frames + 1
		else:
			ctx.num_reorder_frames = sps.max_num_ref_frames

		width_mbs = (sps.pic_width_in_mbs_minus1 + 1)
		height_mbs = (2 - sps.frame_mbs_only_flag) * (sps.pic_height_in_map_units_minus1 + 1)
		assert(width_mbs == (ctx.orig_width + 15) // 16)  # No interlaced
		assert(height_mbs == (ctx.orig_height + 15) // 16)

		level = [level for level in h264_levels if level[1] == sps.level_idc][-1]
		ctx.max_dpb_frames = min((level[5]) // (width_mbs * height_mbs), 16) # max_dpb_mbs
		ctx.rvra_count = ctx.max_dpb_frames + 1 + 1  # all refs + IDR + current
		assert((width_mbs * height_mbs) <= level[4]) # MaxFS
		assert(width_mbs <= sqrt(level[4] * 8))
		assert(height_mbs <= sqrt(level[4] * 8))
		ctx.cur_sps_id = sps_id
		self.allocate_buffers(sl)

	def allocate_buffers(self, sl):
		ctx = self.ctx
		# matching macOS allocations makes for easy diffs
		# see tools/dims264.py experiment
		sps = ctx.get_sps(sl)

		self.reset_allocator()
		ctx.inst_fifo_count = 7
		ctx.inst_fifo_idx = 0  # no FIFO scheduling for single-VP revisions
		ctx.inst_fifo_addrs = [0 for n in range(ctx.inst_fifo_count)]
		self.allocator_move_up(0x4000)
		for n in range(ctx.inst_fifo_count):
			ctx.inst_fifo_addrs[n] = self.range_alloc(0x100000, pad=0x4000, name="inst_fifo%d" % n)
		ctx.inst_fifo_iova = ctx.inst_fifo_addrs[ctx.inst_fifo_idx]

		rvra_total_size = self.calc_rvra(chroma=sps.chroma_format_idc)
		self.allocator_move_up(0x734000)
		ctx.rvra_base_addrs = [0 for n in range(ctx.rvra_count)]
		ctx.rvra_base_addrs[0] = self.range_alloc(rvra_total_size, name="rvra0")

		ctx.luma_size = ctx.fmt.in_width * ctx.fmt.in_height
		ctx.y_addr = self.range_alloc(ctx.luma_size, padb4=0x100, name="disp_y")
		ctx.chroma_size = ctx.fmt.in_width * ctx.fmt.in_height
		if (sps.chroma_format_idc == H264_CHROMA_IDC_420):
			ctx.chroma_size //= 2
		ctx.uv_addr = self.range_alloc(ctx.chroma_size, name="disp_uv")

		ctx.slice_data_size = min((((round_up(ctx.width, 32) - 1) * (round_up(ctx.height, 32) - 1) // 0x8000) + 2), 0xff) * 0x4000
		ctx.slice_data_addr = self.range_alloc(ctx.slice_data_size, align=0x4000, padb4=0x4000, name="slice_data")

		ctx.sps_tile_count = 24
		ctx.sps_tile_addrs = [0 for n in range(ctx.sps_tile_count)]
		sps_tile_size = (((ctx.width - 1) * (ctx.height - 1) // 0x10000) + 2) * 0x4000
		for n in range(ctx.sps_tile_count):
			ctx.sps_tile_addrs[n] = self.range_alloc(sps_tile_size, name="sps_tile%d" % n)

		# Intermediate work tile group #0, 5 tiles based on hw cache line i.e. width stride 16
		pps_tile_count = 5
		ctx.pps_tile_addrs = [0 for n in range(pps_tile_count)]
		for n in range(pps_tile_count):
			if (n == 0):
				# Tile #0: I could not tell you what this means, but it's overwritten on intra frames.
				# Worst 4096x4096 case it still uses <0x8000, which we have to anyway to make tests pass
				"""
				0080c000: 04822000 10000000 38000000 38000000 00000000 00880000 00000000 38000000
				0080c020: 38000000 00000000 00880000 00000000 38000000 38000000 00000000 08800007
				0080c040: 02000000 30000000 38000000 00000000 00000000 00000000 00000000 00000000
				"""
				size = 0x8000
			if (n == 1):
				# Tile #1: Y 1x16, Cb 1x8, Cr 1x8 per row
				"""
				00814000: 51515151 51515151 51515151 51515151 5a5a5a5a 5a5a5a5a f0f0f0f0 f0f0f0f0 ] row
				00814020: 51515151 51515151 51515151 51515151 5a5a5a5a 5a5a5a5a f0f0f0f0 f0f0f0f0
				00814040: 51515151 51515151 51515151 51515151 5a5a5a5a 5a5a5a5a f0f0f0f0 f0f0f0f0
				00814060: 51515151 51515151 51515151 51515151 5a5a5a5a 5a5a5a5a f0f0f0f0 f0f0f0f0
				"""
				size = (1*16 + 1*8 + 1*8) * (round_up(ctx.width, 16) // 16)
			elif (n == 2):
				# Tile #2: Y 2x32, Cb 1x32, Cr 1x32 per row
				"""
				0081c000: 51515151 51515151 51515151 51515151 51515151 51515151 51515151 51515151 ] row
				0081c020: 51515151 51515151 51515151 51515151 51515151 51515151 51515151 51515151 ]
				0081c040: 5a5a5a5a 5a5a5a5a 5a5a5a5a 5a5a5a5a 5a5a5a5a 5a5a5a5a 5a5a5a5a 5a5a5a5a ]
				0081c060: f0f0f0f0 f0f0f0f0 f0f0f0f0 f0f0f0f0 f0f0f0f0 f0f0f0f0 f0f0f0f0 f0f0f0f0 ]
				"""
				size = (2*32 + 1*32 + 1*32) * (round_up(ctx.width, 16) // 16)
				# macOS overallocates a lot so we have to do this to make tests pass
				if (ctx.fmt.in_width > 2048):
					size = 0xc000
			elif (n == 3):
				# Tile #3: No idea what this means, I think it's entropy. 32 bytes per row
				"""
				00824000: c0000000 c0000000 00000000 58000000 04000000 00000000 04000000 00000000 ] row
				00824020: c0000000 c0000000 00000000 50000000 04000000 00000000 04000000 00000000
				00824040: 40000000 40000000 00000000 50000000 00000000 00000000 00000000 00000000
				00824060: c0000000 c0000000 00000000 50000000 04000000 00000000 04000000 00000000
				"""
				size = (1*32) * (round_up(ctx.width, 16) // 16)
			elif (n == 4):
				# Tile #4: Ditto. I think it's reference frame entropy.
				"""
				0082c000: c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 ] row
				0082c020: c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 c0000000
				0082c040: 40000000 40000000 40000000 40000000 40000000 40000000 40000000 40000000
				0082c060: c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 c0000000
				"""
				size = (1*32) * (round_up(ctx.width, 16) // 16)
			size = max(size, 0x8000)
			ctx.pps_tile_addrs[n] = self.range_alloc(size, align=0x4000, name="pps_tile%d" % n)

		for n in range(ctx.rvra_count - 1):
			ctx.rvra_base_addrs[n + 1] = self.range_alloc(rvra_total_size, align=0x4000, name="rvra1_%d" % n)
		self.dump_ranges()

		ctx.dpb_pool = []
		for i in range(ctx.rvra_count):
			pic = AVDH264Picture(addr=ctx.rvra_base_addrs[i], idx=i, pic_num=-1, poc=-1, frame_num_wrap=-1, flags=H264_FRAME_FLAG_UNUSED, access_idx=-1)
			ctx.dpb_pool.append(pic)
			self.log(f"DPB Pool: {pic}")

	def refresh(self, sl):
		self.refresh_sps(sl)
		self.realloc_rbsp_size(sl)

	def init_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		self.refresh(sl)
		self.rlm.init_slice()

	def finish_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		self.rlm.finish_slice()
		self.ctx.access_idx += 1
