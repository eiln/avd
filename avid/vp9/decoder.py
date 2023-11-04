#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..utils import *
from .halv3 import AVDVP9HalV3
from .parser import AVDVP9Parser
from .types import *

class AVDVP9Ctx(dotdict):
	pass

class AVDVP9Decoder:
	def __init__(self):
		self.parser = AVDVP9Parser()
		self.hal = AVDVP9HalV3()
		self.ctx = None
		self.stfu = False

	def log(self, x):
		if (not self.stfu):
			if (self.ctx) and hasattr(self.ctx, "active_sl"):
				print(f"[AVD] {self.ctx.active_sl.idx}: {x}")
			else:
				print(f"[AVD] {x}")

	def parse(self, path):
		units = self.parser.parse(path)
		self.setup()
		return units

	def setup(self):
		self.ctx = AVDVP9Ctx()
		ctx = self.ctx
		ctx.inst_fifo_idx = 0
		ctx.inst_fifo_count = 6
		ctx.access_idx = 0
		ctx.active_sl = None

		ctx.y_addr = 0x768100
		ctx.uv_addr = 0x76c900
		ctx.slice_data_addr = 0x774000

		# m1n1 compat
		ctx.width = 128
		ctx.height = 64
		ctx.inst_fifo_iova = 0x2c000

	def init_slice(self):
		ctx = self.ctx

	def finish_slice(self):
		ctx = self.ctx
		ctx.access_idx += 1

	def generate(self, sl):
		self.ctx.active_sl = sl
		self.init_slice()
		inst = self.hal.generate(self.ctx, sl)
		self.finish_slice()
		return inst
