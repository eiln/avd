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

class AVDVP9Decoder(AVDDecoder):
	def __init__(self):
		super().__init__(AVDVP9Parser, AVDVP9HalV3, AVDVP9V3FrameParams)
		self.mode = "vp09"
		self.probscls = AVDVP9Probs

	def new_context(self):
		self.ctx = AVDVP9Ctx()
		ctx = self.ctx

		ctx.access_idx = 0
		ctx.kidx = 0
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
		ctx.dpb = []

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

		ctx.pps_tile_addrs = [0] * 4

		if   (ctx.width == 128 and ctx.height == 64):
			ctx.sps_tile_base_addr = 0x8cc000 >> 8  # [0x8cc0, 0x8d40, 0x8e40, 0x8ec0, 0x8f40, 0x8fc0]
			ctx.pps_tile_base_addr = 0x87c000 >> 8  # [0x8dc0, 0x8940, 0x87c0, 0x8840]
			ctx.pps_tile_addrs[3] = ctx.pps_tile_base_addr + 0x80
			ctx.pps_tile_addrs[1] = ctx.pps_tile_base_addr + 0x80 + 0x100          # 0x180
			ctx.pps_tile_addrs[0] = ctx.pps_tile_base_addr + 0x80 + 0x100 + 0x480  # 0x600

			ctx.rvra0_base_addrs  = [0x0ef80, 0x0eb82, 0x0f080, 0x0ec12]
			ctx.rvra1_base_addrs  = [0x0f180, 0x12082, 0x0f280, 0x12112] # [+0x200, +0x3500, +0x200, +0x3500]
			ctx.rvra1_even_offset = 0x200
			ctx.rvra1_odd_offsets = [0x300, 0x600, 0x180]

			ctx.y_addr = 0x768100
			ctx.uv_addr = 0x76c900
			ctx.slice_data_addr = 0x774000
			ctx.height_width_align = 0xc  # ctx.width >> 6 << 2

		elif (ctx.width == 1024 and ctx.height == 512):
			ctx.sps_tile_base_addr = 0x9d4000 >> 8  # [0x9d40, 0x9dc0, 0x9ec0, 0x9f40, 0x9fc0, 0xa040]
			ctx.pps_tile_base_addr = 0x964000 >> 8  # [0x9e40, 0x99c0, 0x9640, 0x97c0]
			ctx.pps_tile_addrs[3] = ctx.pps_tile_base_addr + 0x180
			ctx.pps_tile_addrs[1] = ctx.pps_tile_base_addr + 0x180 + 0x200  # 0x380
			ctx.pps_tile_addrs[0] = ctx.pps_tile_base_addr + 0x180 + 0x200 + 0x480  # 0x800

			ctx.rvra0_base_addrs  = [0x0ff80, 0x0eb80, 0x10a00, 0x10000]
			ctx.rvra1_base_addrs  = [0x15780, 0x14380, 0x16200, 0x15800] # [+0x200, +0x3500, +0x200, +0x3500]
			ctx.rvra1_even_offset = 0x3880
			ctx.rvra1_odd_offsets = [0x3880, 0x7100]

			ctx.y_addr = 0x858100
			ctx.uv_addr = 0x8d8100
			ctx.slice_data_addr = 0x920000
			ctx.height_width_align = 0x40

		else:
			raise ValueError("not impl")

		ctx.pps_tile_addrs[2] = ctx.pps_tile_base_addr + 0x0

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

	def init_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		if (sl.frame_type == VP9_FRAME_TYPE_KEY):
			ctx.kidx = 0
			ctx.num_kf += 1
			ctx.acc_refresh_mask = 0b00000000
			sl.refresh_frame_flags = 0xff
		self.refresh(sl)

	def finish_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl

		ctx.dpb.append(ctx.curr_rvra_addrs)

		ctx.access_idx += 1
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
