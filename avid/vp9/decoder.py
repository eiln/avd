#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..decoder import AVDDecoder
from ..utils import *
from .halv3 import AVDVP9HalV3
from .parser import AVDVP9Parser
from .probs import AVDVP9Probs
from .types import *

class AVDVP9Ctx(dotdict):
	pass

class AVDVP9Decoder(AVDDecoder):
	def __init__(self):
		super().__init__(AVDVP9Parser, AVDVP9HalV3)

	def new_context(self):
		self.ctx = AVDVP9Ctx()
		ctx = self.ctx

		ctx.access_idx = 0
		ctx.width = -1
		ctx.height = -1
		ctx.active_sl = None

		ctx.inst_fifo_count = 7
		ctx.inst_fifo_idx = 0

	def allocate(self):
		ctx = self.ctx
		# constants
		ctx.inst_fifo_iova = 0x2c000
		ctx.inst_fifo_size = 0x100000
		ctx.probs_size = AVDVP9Probs.sizeof() # 0x774
		ctx.probs_count = 4  # rotating FIFO slots
		ctx.probs_base_addr = 0x4000  # (round_up(ctx.probs_size), 0x4000) * ctx.probs_count

		ctx.y_addr = 0x768100
		ctx.uv_addr = 0x76c900
		ctx.slice_data_addr = 0x774000

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

	def setup(self, path):
		self.new_context()
		slices = self.parser.parse(path)
		self.refresh(slices[0])
		return slices

	def init_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		self.refresh(sl)

	def finish_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		ctx.access_idx += 1
