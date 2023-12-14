#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..decoder import AVDDecoder, AVDOutputFormat
from ..utils import *
from .fp import AVDH265V3FrameParams
from .halv3 import AVDH265HalV3
from .parser import AVDH265Parser
from .rlm import AVDH265RLM, AVDH265Picture
from .types import *

class AVDH265Ctx(dotdict):
	def get_pps(self, sl):
		return sl.pps

	def get_sps(self, sl):
		return sl.sps

	def rvra_offset(self, idx):
		if   (idx == 0): return self.rvra_size0
		elif (idx == 1): return 0
		elif (idx == 2): return self.rvra_size0 + self.rvra_size1 + self.rvra_size2
		elif (idx == 3): return self.rvra_size0 + self.rvra_size1
		raise ValueError("invalid rvra group (%d)" % idx)

class AVDH265Decoder(AVDDecoder):
	def __init__(self):
		super().__init__(AVDH265Parser, AVDH265HalV3, AVDH265V3FrameParams)
		self.mode = "h265"
		self.rlm = AVDH265RLM(self)

	def new_context(self, vps_list, sps_list, pps_list):
		self.ctx = AVDH265Ctx()
		ctx = self.ctx
		ctx.vps_list = vps_list
		ctx.sps_list = sps_list
		ctx.pps_list = pps_list

		ctx.access_idx = 0
		ctx.width = -1
		ctx.height = -1
		ctx.active_sl = None
		ctx.cur_sps_id = -1

		ctx.last_intra_nal_type = -1
		ctx.last_intra = 0
		ctx.last_p_sps_tile_idx = 0
		ctx.dpb_list = []
		ctx.ref_lst = [[None for n in range(64)] for n in range(5)]
		ctx.ref_lst_cnt = [0, 0, 0, 0, 0]
		ctx.poc = -1
		self.rlm.ctx = ctx

	def refresh_sps(self, sl):
		ctx = self.ctx
		pps = ctx.get_pps(sl)
		sps_id = pps.pps_seq_parameter_set_id
		if (sps_id == ctx.cur_sps_id):
			return
		sps = ctx.sps_list[sps_id]

		# TODO multiple slices with pointing to different SPSs, sigh
		width = sps.pic_width_in_luma_samples
		height = sps.pic_height_in_luma_samples
		ctx.orig_width = width
		ctx.orig_height = height
		if (width & 1):
			width = round_up(width, 2)
		if (height & 1):
			height = round_up(height, 2)
		if ((width != ctx.orig_width) or (height != ctx.orig_height)):
			self.log("dimensions changed from %dx%d -> %dx%d" % (ctx.width, ctx.height, width, height))
		ctx.width = width
		ctx.height = height

		assert((64 <= width and width <= 4096) and (64 <= height and height <= 4096)) # hardware caps
		assert(not(width & 1) and not(height & 1)) # hardware caps

		ctx.fmt = AVDOutputFormat(
			in_width=(round_up(ctx.width, 64) >> 4) << 4,
			in_height=ctx.height,
			out_width=ctx.orig_width,
			out_height=ctx.orig_height,
			chroma=sps.chroma_format_idc,
		)
		ctx.fmt.x0 = 0
		ctx.fmt.x1 = ctx.fmt.out_width  # TODO vui frame crop
		ctx.fmt.y0 = 0
		ctx.fmt.y1 = ctx.fmt.out_height
		self.log(ctx.fmt)
		assert(ctx.fmt.in_width >= ctx.fmt.out_width)
		assert(ctx.fmt.in_height >= ctx.fmt.out_height)

		ctx.cur_sps_id = sps_id
		self.allocate_buffers(sl)

	def allocate_buffers(self, sl):
		ctx = self.ctx
		sps = ctx.get_sps(sl)
		pps = ctx.get_pps(sl)

		self.reset_allocator()
		ctx.inst_fifo_count = 7
		ctx.inst_fifo_idx = 0
		ctx.inst_fifo_addrs = [0 for n in range(ctx.inst_fifo_count)]
		self.allocator_move_up(0x18000)
		for n in range(ctx.inst_fifo_count):
			ctx.inst_fifo_addrs[n] = self.range_alloc(0x100000, pad=0x4000, name="inst_fifo%d" % n)
		ctx.inst_fifo_iova = ctx.inst_fifo_addrs[ctx.inst_fifo_idx]

		rvra_total_size = self.calc_rvra(chroma=sps.chroma_format_idc)
		self.allocator_move_up(0x734000)
		ctx.rvra_count = 6
		ctx.rvra_base_addrs = [0 for n in range(ctx.rvra_count)]
		ctx.rvra_base_addrs[0] = self.range_alloc(rvra_total_size, pad=0x100, name="rvra0")

		ctx.luma_size = ctx.fmt.in_width * ctx.fmt.in_height
		ctx.y_addr = self.range_alloc(ctx.luma_size, name="disp_y")
		ctx.chroma_size = ctx.fmt.in_width * round_up(ctx.height, 16)
		if (sps.chroma_format_idc == HEVC_CHROMA_IDC_420):
			ctx.chroma_size //= 2
		ctx.uv_addr = self.range_alloc(ctx.chroma_size, name="disp_uv")

		ctx.slice_data_size = min((((round_up(ctx.width, 32) - 1) * (round_up(ctx.height, 32) - 1) // 0x8000) + 2), 0xff) * 0x4000
		ctx.slice_data_addr = self.range_alloc(ctx.slice_data_size, align=0x4000, padb4=0x4000, name="slice_data")

		ctx.sps_tile_count = 16
		ctx.sps_tile_addrs = [0 for n in range(ctx.sps_tile_count)]
		n = max(rounddiv(ctx.height * ctx.width, 0x40000), 1) + 1
		sps_tile_size = n * 0x4000
		for n in range(ctx.sps_tile_count):
			ctx.sps_tile_addrs[n] = self.range_alloc(sps_tile_size, name="sps_tile%d" % n)

		if (pps.tiles_enabled_flag):
			pps_tile_count = 8
		else:
			pps_tile_count = 5
		ctx.pps_tile_addrs = [0 for n in range(pps_tile_count)]
		for n in range(pps_tile_count):
			ctx.pps_tile_addrs[n] = self.range_alloc(0x8000, name="pps_tile%d" % n)
		if (pps.tiles_enabled_flag):
			self.allocator_move_up(self.last_iova + 0x20000)

		for n in range(ctx.rvra_count - 1):
			ctx.rvra_base_addrs[n + 1] = self.range_alloc(rvra_total_size, name="rvra1_%d" % n)
		self.dump_ranges()

		ctx.dpb_pool = []
		for i in range(ctx.rvra_count):
			pic = AVDH265Picture(addr=ctx.rvra_base_addrs[i], idx=i, poc=-1, flags=0, type=-1, lsb7=True, rasl=0, access_idx=-1)
			ctx.dpb_pool.append(pic)
			self.log(f"DPB Pool: {pic}")

	def realloc_rbsp_size(self, sl):
		ctx = self.ctx
		size = len(sl.get_payload())
		for seg in sl.slices:
			size += len(seg.get_payload())
		if (size > ctx.slice_data_size):
			self.range_free(name="slice_data")
			ctx.slice_data_addr = self.range_alloc(size, align=0x4000, name="slice_data")
			ctx.slice_data_size = size
		sl.payload_addr = ctx.slice_data_addr
		offset = len(sl.get_payload())
		for seg in sl.slices:
			seg.payload_addr = ctx.slice_data_addr + offset
			offset += len(seg.get_payload())

	def refresh(self, sl):
		self.refresh_sps(sl)
		self.realloc_rbsp_size(sl)

	def setup(self, path, num=0, **kwargs):
		vps_list, sps_list, pps_list, slices = self.parser.parse(path, num=num)
		self.new_context(vps_list, sps_list, pps_list)
		return slices

	def init_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		self.refresh(sl)
		poc = sl.pic_order_cnt
		for i,s in enumerate([sl] + sl.slices):
			assert(not (i == 0 and s.dependent_slice_segment_flag))
			if (not s.dependent_slice_segment_flag):
				if (i == 0 or s.slice_type != HEVC_SLICE_I):
					s.pic = self.rlm.set_new_ref(s, poc)
				self.rlm.do_frame_rps(s)
				if (s.slice_type != HEVC_SLICE_I):
					s.reflist = self.rlm.construct_ref_list(s)

	def finish_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		if (IS_IDR2(sl)):
			ctx.last_intra_nal_type = sl.nal_unit_type
		ctx.last_intra = IS_INTRA(sl)
		ctx.access_idx += 1
