#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..decoder import AVDDecoder
from ..utils import *
from .fp import AVDVP9V3FrameParams
from .halv3 import AVDVP9HalV3
from .parser import AVDVP9Parser
from .probs import AVDVP9Probs
from .types import *
from copy import deepcopy

class AVDVP9Ctx(dotdict):
	pass

class AVDVP9RefBuffer(dotdict):
	def __repr__(self):
		return f"[refbuf {self.idx}: ref_count: {self.ref_count}]"

	def decrease_ref_count(self):
		self.ref_count -= 1

class AVDVP9Decoder(AVDDecoder):
	def __init__(self):
		super().__init__(AVDVP9Parser, AVDVP9HalV3, AVDVP9V3FrameParams)
		self.mode = "vp09"
		self.probscls = AVDVP9Probs

	def new_context(self):
		self.ctx = AVDVP9Ctx()
		ctx = self.ctx

		ctx.access_idx = 0
		ctx.width = -1
		ctx.height = -1
		ctx.active_sl = None
		ctx.num_kf = 0
		ctx.last_kf = 0
		ctx.kidx = 0
		ctx.last_flag = -1
		ctx.acc_refresh_mask = 0

		ctx.inst_fifo_count = 7
		ctx.inst_fifo_idx = 0

		ctx.frame_bufs = [AVDVP9RefBuffer(dict(ref_count=0, idx=n)) for n in range(VP9_FRAME_BUFFERS)]
		ctx.ref_frame_map = [-1] * VP9_REF_FRAMES
		ctx.next_ref_frame_map = [-1] * VP9_REF_FRAMES
		ctx.new_fb_idx = -1
		ctx.idx_map = {}

	def allocate(self):
		ctx = self.ctx
		# constants
		ctx.inst_fifo_iova = 0x2c000
		ctx.inst_fifo_size = 0x100000
		# [0x002c0, 0x01300, 0x02340, 0x03380, 0x043c0, 0x05400, 0x06440]
		# ctx.inst_fifo_iova + (n * (ctx.inst_fifo_size + 0x4000))

		ctx.probs_size = AVDVP9Probs.sizeof() # 0x774
		ctx.probs_count = 4  # rotating FIFO slots
		ctx.probs_base_addr = 0x4000  # (round_up(ctx.probs_size), 0x4000) * ctx.probs_count

		if   (ctx.width == 128 and ctx.height == 64):
			ctx.sps_tile_base_addr = 0x8cc000 >> 8  # [0x8cc0, 0x8d40, 0x8e40, 0x8ec0, 0x8f40, 0x8fc0]
			ctx.pps0_tile_addr = 0x8dc0
			ctx.pps1_tile_base = 0x88c0
			ctx.pps2_tile_addrs = [0x87c0, 0x8840]

			ctx.rvra0_addrs = [0x0ef80, 0x0f180, 0x0f380, 0x0f580]
			ctx.rvra2_addrs = [0x0f080, 0x0f280, 0x0f480, 0x0f680]
			ctx.rvra1_addrs = [0x0eb82, 0x012082, 0x012382, 0x12682]
			ctx.rvra3_addrs = [0x0ec12, 0x012112, 0x012682, 0x012202]
			ctx.y_addr = 0x768100
			ctx.uv_addr = 0x76c900
			ctx.slice_data_addr = 0x774000
			ctx.height_width_align = 0xc  # ctx.width >> 6 << 2

		elif (ctx.width == 1024 and ctx.height == 512):
			ctx.sps_tile_base_addr = 0x9d4000 >> 8  # [0x9d40, 0x9dc0, 0x9ec0, 0x9f40, 0x9fc0, 0xa040]
			ctx.pps0_tile_addr = 0x9e40
			ctx.pps2_tile_addrs = [0x9640, 0x97c0]
			ctx.pps1_tile_base = 0x9940

			ctx.rvra0_addrs = [0xff80, 0x15780, 0x19000, 0x1c880]
			ctx.rvra2_addrs = [0x10a00, 0x16200, 0x19a80, 0x1d300]
			ctx.rvra1_addrs = [0xeb80, 0x14380, 0x17c00, 0x1b480]
			ctx.rvra3_addrs = [0x10000, 0x15800, 0x19080, 0x1c900]

			ctx.y_addr = 0x858100
			ctx.uv_addr = 0x8d8100
			ctx.slice_data_addr = 0x920000
			ctx.height_width_align = 0x40

		else:
			raise ValueError("not impl")

		ctx.pps1_tile_size = 0x8000
		ctx.pps1_tile_count = 8
		ctx.pps1_tile_addrs = [0] * ctx.pps1_tile_count
		for n in range(ctx.pps1_tile_count):
			ctx.pps1_tile_addrs[n] = ctx.pps1_tile_base + (ctx.pps1_tile_size >> 8) * n

	def refresh(self, sl):
		ctx = self.ctx
		width = sl.frame_width
		height = sl.frame_height
		if (not ((width == ctx.width) and (height == ctx.height))):
			self.log("dimensions changed from %dx%d -> %dx%d" % (ctx.width, ctx.height, width, height))
			ctx.width = width
			ctx.height = height
			self.allocate()

		# update addresses driver needs to access
		probs_slot = ctx.access_idx % ctx.probs_count
		# plus a page for some reason
		ctx.probs_addr = ctx.probs_base_addr + (probs_slot * (round_up(ctx.probs_size, 0x4000) + 0x4000))

	def setup(self, path, num=0, do_probs=1, **kwargs):
		self.new_context()
		slices = self.parser.parse(path, num, do_probs)
		self.refresh(slices[0])
		return slices

	def get_free_fb(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		n = 0
		for i in range(VP9_FRAME_BUFFERS):
			if (ctx.frame_bufs[i].ref_count <= 0):
				break
			n += 1
		if (n != VP9_FRAME_BUFFERS):
			ctx.frame_bufs[n].ref_count = 1
		else:
			n = -1
		return n

	def gen_ref_map(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		ctx.new_fb_idx = self.get_free_fb()
		assert((ctx.new_fb_idx != -1))

		ref_index = 0
		for i in range(8):
			if (sl.refresh_frame_flags & (1 << i)):
				ctx.next_ref_frame_map[ref_index] = ctx.new_fb_idx
				ctx.frame_bufs[ctx.new_fb_idx].ref_count += 1
			else:
				ctx.next_ref_frame_map[ref_index] = ctx.ref_frame_map[ref_index]

			#if (ctx.ref_frame_map[ref_index] >= 0):
			#	ctx.frame_bufs[ctx.ref_frame_map[ref_index]].ref_count += 1
			ref_index += 1

	def swap_frame_buffers(self):
		ctx = self.ctx; sl = self.ctx.active_sl

		ref_index = 0
		for i in range(8):
			old_idx = ctx.ref_frame_map[ref_index]
			#if (old_idx != -1):
			#	ctx.frame_bufs[old_idx].decrease_ref_count()
			if (sl.refresh_frame_flags & (1 << i)):
				ctx.frame_bufs[old_idx].decrease_ref_count()
			ctx.ref_frame_map[ref_index] = ctx.next_ref_frame_map[ref_index]
			ref_index += 1

		ctx.frame_bufs[ctx.new_fb_idx].decrease_ref_count()

	def init_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		if (sl.frame_type == VP9_FRAME_TYPE_KEY):
			ctx.kidx = 0
			ctx.num_kf += 1
			ctx.acc_refresh_mask = 0b00000000
			sl.refresh_frame_flags = 0xff
		self.refresh(sl)
		self.gen_ref_map()

	def finish_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl

		self.swap_frame_buffers()
		if (sl.frame_type != VP9_FRAME_TYPE_KEY):
			ctx.kidx += 1
		if (ctx.kidx == 1):
			ctx.acc_refresh_mask |= sl.refresh_frame_flags & 0b1
		if (ctx.kidx >= 2):
			ctx.acc_refresh_mask |= sl.refresh_frame_flags

		if (sl.frame_type == VP9_FRAME_TYPE_KEY):
			ctx.last_kf = 1
		else:
			ctx.last_kf = 0
		ctx.last_flag = sl.refresh_frame_flags

		ctx.access_idx += 1
