#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

class AVDDecoder:
	def __init__(self, parsercls, halcls):
		self.parser = parsercls()
		self.hal = halcls()
		self.ctx = None
		self.stfu = False

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

	def generate(self, sl):
		self.ctx.active_sl = sl
		self.init_slice()
		inst = self.hal.generate(self.ctx, sl)
		self.finish_slice()
		return inst
