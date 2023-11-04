#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..parser import AVDParser, AVDSlice
from .types import *

class AVDVP9Slice(AVDSlice):
	def __init__(self):
		super().__init__()

	def __repr__(self):
		s = "\n[slice: %d key_frame: %d]\n" % (self.idx, not self.frame_type)
		s += self.show_entries()
		return s

	def get_payload(self):
		pass

	def get_payload_offset(self):
		#return ceil(self.header_size / 8) + 4
		return 4

	def get_payload_size(self):
		return 0xdead

class AVDVP9Parser(AVDParser):
	def __init__(self):
		super().__init__("vp9.out", "")
		self.arr_keys = [
			("ref_frame_idx", VP9_REF_FRAMES),
			("ref_frame_sign_bias", VP9_REF_FRAMES),
			("loop_filter_ref_deltas", VP9_MAX_REF_LF_DELTAS),
			("loop_filter_mode_deltas", VP9_MAX_MODE_LF_DELTAS),
		]
		self.slccls = AVDVP9Slice

	def parse(self, path):
		return self.get_headers(path)
