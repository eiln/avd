#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

class AVDDecoder:
	def __init__(self, parsercls, halcls, fpcls):
		self.parser = parsercls()
		self.hal = halcls()
		self.fpcls = fpcls
		self.ctx = None
		self.stfu = False
		self.ffp = {}

	def log(self, x):
		if (not self.stfu):
			print(f"[AVD] {x}")

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
