#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from collections import namedtuple
from dataclasses import dataclass
from .utils import *

@dataclass(slots=True)
class AVDOutputFormat:
	in_width: int
	in_height: int
	out_width: int
	out_height: int
	x0: int = 0
	x1: int = 0
	y0: int = 0
	y1: int = 0
	chroma: int = 0

class AVDRange(namedtuple('AVDRange', ['iova', 'size', 'name'])):
	def __repr__(self):
		return f"[iova: {hex(self.iova).rjust(7+2)} size: {hex(self.size).rjust(7+2)} name: {str(self.name).ljust(11)}]"

class AVDDecoder:
	def __init__(self, parsercls, halcls, fpcls):
		self.parser = parsercls()
		self.hal = halcls()
		self.fpcls = fpcls
		self.ctx = None
		self.stfu = False
		self.ffp = {}
		self.last_iova = 0x0
		self.used = []

	def log(self, x):
		if (not self.stfu):
			print(f"[AVD] {x}")

	def reset_allocator(self):
		self.last_iova = 0x0
		self.used = []

	def range_alloc(self, size, pad=0x0, padb4=0x0, align=0x0, name=""):
		iova = self.last_iova
		if (align):
			iova = round_up(iova, align)
		if (padb4):
			iova += padb4
		if (not name):
			name = "range_%d" % len(self.used)
		self.used.append(AVDRange(iova, size, name))
		self.last_iova = iova + size + pad
		return iova

	def allocator_move_up(self, start):
		assert(start >= self.last_iova)
		self.last_iova = start

	def range_free(self, name):
		self.used = [x for x in self.used if x.name != name]

	def allocator_top(self):
		return self.last_iova

	def realloc_rbsp_size(self, sl):
		ctx = self.ctx
		size = len(sl.get_payload())
		if (size > ctx.slice_data_size):
			self.range_free(name="slice_data")
			ctx.slice_data_addr = self.range_alloc(size, align=0x4000, name="slice_data")
			ctx.slice_data_size = size

	def dump_ranges(self):
		for i,x in enumerate(self.used):
			s = f"[{str(i).rjust(2)}] {x}"
			if ("rvra" in x.name):
				s += f" {hex(x.iova >> 7).rjust(5+2)}"
			self.log(s)
		self.log("last iova: 0x%08x" % (self.last_iova))

	def init_slice(self):
		pass

	def finish_slice(self):
		pass

	def refresh(self, sl): # sl is RO
		pass

	def setup(self, path):
		raise NotImplementedError()

	def decode(self, sl):
		self.ctx.active_sl = sl
		self.init_slice()
		inst_stream = self.hal.decode(self.ctx, sl)
		self.ffp = self.make_ffp(inst_stream)
		self.finish_slice()
		return inst_stream

	def make_ffp(self, inst_stream):
		ffp = self.fpcls._ffpcls.new()
		for inst in inst_stream:
			if (isinstance(inst.idx, int)):
				ffp[inst.name][inst.idx] = inst.val
			else:
				ffp[inst.name] = inst.val
		return ffp

	def calc_rvra(self, chroma):
		ctx = self.ctx
		# reference VRA (video resolution adaptation) scaler buffer.
		ws = round_up(ctx.width, 32)
		hs = round_up(ctx.height, 32)
		ctx.rvra_size0 = (ws * hs) + ((ws * hs) // 4)
		ctx.rvra_size2 = ctx.rvra_size0
		if   (chroma == 0):   # 4:0:0
			ctx.rvra_size2 *= 0
		elif (chroma == 1): # 4:2:0
			ctx.rvra_size2 //= 2
		ctx.rvra_size1 = max(nextpow2(ctx.width) * nextpow2(ctx.height) // 32, 0x100)
		size = ctx.rvra_size0 + ctx.rvra_size1 + ctx.rvra_size2
		size = round_up(size, 0x4000)
		# TODO
		d = 1
		if (ctx.width >= 1000):
			d = 2
		if (ctx.width >= 1800):
			d = 3
		if (ctx.width >= 3800):
			d = 9
		size += d * 0x4000
		ctx.rvra_total_size = size
		ctx.rvra_size3 = ctx.rvra_total_size - (ctx.rvra_size0 + ctx.rvra_size1 + ctx.rvra_size2)
		return ctx.rvra_total_size
