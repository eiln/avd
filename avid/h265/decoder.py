#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..decoder import AVDDecoder
from ..utils import *
from .fp import AVDH265V3FrameParams
from .halv3 import AVDH265HalV3
from .parser import AVDH265Parser
from .types import *
from math import sqrt

class AVDH265Ctx(dotdict):
	pass

class AVDH265Picture(dotdict):
	def __repr__(self):
		return f"[addr: {hex(self.addr >> 7).ljust(2+5)} poc: {str(self.poc).rjust(3)} idx: {str(self.idx).rjust(2)}]"

class AVDH265Decoder(AVDDecoder):
	def __init__(self):
		super().__init__(AVDH265Parser, AVDH265HalV3, AVDH265V3FrameParams)
		self.mode = "h265"

	def get_pps(self, sl):
		return self.ctx.pps_list[sl.slice_pic_parameter_set_id]

	def get_sps_id(self, sl):
		return self.get_pps(sl).pps_seq_parameter_set_id

	def get_sps(self, sl):
		return self.ctx.sps_list[self.get_sps_id(sl)]

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

		ctx.last_p_sps_tile_idx = 0
		ctx.prev_poc_lsb = 0
		ctx.prev_poc_msb = 0
		ctx.dpb_list = []
		ctx.unused_refs = []
		ctx.drain_list = []
		ctx.rvra_pool_count = 0

		ctx.inst_fifo_count = 6
		ctx.inst_fifo_idx = 0

	def refresh(self, sl):
		ctx = self.ctx
		sps_id = self.get_sps_id(sl)
		if (sps_id == ctx.cur_sps_id):
			return
		sps = ctx.sps_list[sps_id]

		width = sps.pic_width_in_luma_samples
		height = sps.pic_height_in_luma_samples

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

		assert((64 <= width and width <= 4096) and (64 <= height and height <= 4096)) # hardware caps
		assert(not(width & 15) and not(height & 15)) # hardware caps
		ctx.cur_sps_id = sps_id
		self.allocate()

	def allocate(self):
		ctx = self.ctx
		sps = ctx.sps_list[ctx.cur_sps_id]

		# constants
		ctx.inst_fifo_iova = 0x4000
		ctx.inst_fifo_size = 0x100000
		ctx.pps_tile_count = 5  # just random work buffers; they call it sps/pps for non-mpeg codecs too
		ctx.pps_tile_size = 0x8000
		ctx.sps_tile_count = 24  # again, nothing to do with sps; just a name for work buf group 2
		ctx.rvra0_addr = 0x734000

		ws = round_up(ctx.width, 32)
		hs = round_up(ctx.height, 32)
		ctx.rvra_size0 = (ws * hs) + ((ws * hs) // 4) # 1. luma padded to stride 32, 4x4
		ctx.rvra_size2 = ctx.rvra_size0  # 2. chroma, 422
		if (sps.chroma_format_idc == HEVC_CHROMA_IDC_420):
			ctx.rvra_size2 //= 2

		# 3. luma weights, likely
		ctx.rvra_size1 = ((nextpow2(ctx.height) // 32) * nextpow2(ctx.width))
		# 4. chroma weights, likely. can't figure this one out, sorry guys
		if (ctx.width == 128 and ctx.height == 64):
			ctx.rvra_size3 = 0x4300
		elif (ctx.width == 1024 and ctx.height == 512):
			ctx.rvra_size3 = 0x8000
		elif (ctx.width == 1920 and ctx.height == 1088):
			ctx.rvra_size3 = 0xfc00
		elif (ctx.width == 3840 and ctx.height == 2160):
			ctx.rvra_size3 = 0x27000
		else:   # worst case, oops
			ctx.rvra_size3 = 0x40000

		ctx.rvra_total_size = ctx.rvra_size0 + ctx.rvra_size1 + ctx.rvra_size2 + ctx.rvra_size3
		ctx.rvra_count = 8 + 1 + 1  # all refs + IDR + current

		ctx.y_addr = ctx.rvra0_addr + ctx.rvra_total_size + 0x100

		if (not(isdiv(ctx.width, 32))):
			wr = round_up(ctx.width, 64)
		else:
			wr = ctx.width
		luma_size = wr * ctx.height
		ctx.uv_addr = ctx.y_addr + luma_size
		chroma_size = wr * ctx.height
		ctx.slice_data_addr = round_up(ctx.uv_addr + chroma_size, 0x4000)

		ctx.slice_data_size = min((((ws - 1) * (hs - 1) // 0x8000) + 2), 0xff) * 0x4000
		ctx.sps_tile_addr = ctx.slice_data_addr + ctx.slice_data_size
		ctx.sps_tile_size = (((ctx.width - 1) * (ctx.height - 1) // 0x10000) + 2) * 0x4000

		pps_tile_addrs = [0] * ctx.pps_tile_count
		pps_tile_base_addr = ctx.sps_tile_addr + (ctx.sps_tile_size * ctx.sps_tile_count)
		addr = pps_tile_base_addr
		for n in range(ctx.pps_tile_count):
			pps_tile_addrs[n] = addr
			addr += 0x8000
		ctx.pps_tile_addrs = pps_tile_addrs
		ctx.rvra1_addr = addr

	def setup(self, path, num=0, **kwargs):
		vps_list, sps_list, pps_list, slices = self.parser.parse(path, num=num)
		self.new_context(vps_list, sps_list, pps_list)
		# realistically we'd have the height/width as metadata w/o relying on sps
		self.refresh(slices[0])
		return slices

	def get_next_rvra(self):
		return self.ctx.access_idx

	def get_rvra_addr(self, idx):
		ctx = self.ctx
		if (idx % ctx.rvra_count == 0): return ctx.rvra0_addr
		else: return ctx.rvra1_addr + (((idx % ctx.rvra_count) - 1) * ctx.rvra_total_size)

	def construct_ref_list_p(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		short_refs = [pic for pic in ctx.dpb_list if pic.type == HEVC_REF_ST]
		short_refs = sorted(short_refs, key=lambda pic: pic.frame_num_wrap, reverse=True)
		for ref in short_refs:
			self.log(f"P: ST Refs: {ref}")
		sl.pic.short_refs = short_refs
		list0 = short_refs
		if (sl.ref_pic_list_modification_flag_l0):
			list0 = self.modify_ref_list(list0, 0)
		sl.pic.list0 = list0

	def construct_ref_list_b(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		short_refs = [pic for pic in ctx.dpb_list if pic.type == HEVC_REF_ST]
		short_refs = sorted(short_refs, key=lambda pic: pic.poc, reverse=True)
		for ref in short_refs:
			self.log(f"B: ST Refs: {ref}")
		sl.pic.short_refs = short_refs
		list0 = sorted([pic for pic in short_refs if pic.poc < sl.pic.poc], key=lambda pic: pic.poc, reverse=True)
		list1 = sorted([pic for pic in short_refs if pic.poc > sl.pic.poc], key=lambda pic: pic.poc)
		if (sl.ref_pic_list_modification_flag_l0):
			list0 = self.modify_ref_list(list0, 0)
		if (sl.ref_pic_list_modification_flag_l1):
			list1 = self.modify_ref_list(list1, 1)
		sl.pic.list0 = list0
		sl.pic.list1 = list1

	def construct_ref_list(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		if (sl.slice_type == HEVC_SLICE_P):
			self.construct_ref_list_p()
		elif (sl.slice_type == HEVC_SLICE_B):
			self.construct_ref_list_b()

	def init_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		self.refresh(sl)

		sl.pic = AVDH265Picture()
		sl.pic.type = HEVC_REF_ST
		sl.pic.poc = sl.pic_order_cnt_lsb
		sl.pic.idx = self.get_next_rvra()
		sl.pic.addr = self.get_rvra_addr(sl.pic.idx)
		sl.pic.access_idx = ctx.access_idx
		sl.pic.frame_num_wrap = sl.pic_order_cnt_lsb
		sl.pic.pic_num = sl.pic_order_cnt_lsb
		self.construct_ref_list()

	def finish_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl

		if (IS_IDR(sl) or 1):
			self.log(f"Adding pic to dpb {sl.pic}")
			ctx.dpb_list.append(sl.pic)
			ctx.unused_refs = [i for i in ctx.unused_refs if i.addr != sl.pic.addr]

		if (IS_IDR(sl) or 1):
			max_num_ref_frames = 3
			if (len(ctx.dpb_list) > max_num_ref_frames):
				oldest = sorted(ctx.dpb_list, key=lambda pic: pic.access_idx)[0]
				self.log(f"ADPT: removing oldest ref {oldest}")
				ctx.dpb_list = [x for x in ctx.dpb_list if x != oldest]
				ctx.unused_refs.append(oldest)

		if (sl.slice_type == HEVC_SLICE_P):
			ctx.last_p_sps_tile_idx = ctx.access_idx % ctx.sps_tile_count
		self.ctx.access_idx += 1
