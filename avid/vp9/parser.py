#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..parser import AVDParser, AVDSlice
from ..types import *
from .types import *
from construct import *

IVFHeader = Struct(
	"signature" / ExprValidator(PaddedString(4, encoding='u8'), obj_ == "DKIF"),
	"version" / ExprValidator(Int16ul, obj_ == 0),
	"length" / ExprValidator(Int16ul, obj_ == 32),
	"fourcc" / PaddedString(4, encoding='u8'),
	"width" / Int16ul,
	"height" / Int16ul,
	"frame_rate_rate" / Int32ul,
	"frame_rate_scale" / Int32ul,
	"frame_count" / Int32ul,
	"reserved" / Padding(4),
)
assert(IVFHeader.sizeof() == 32)

IVFFrameHeader = Struct(
	"size" / Int32ul,
	"timestamp" / Int64ul,
)
assert(IVFFrameHeader.sizeof() == 12)

class IVFFrame:
	def __init__(self, f, b):
		self.payload = b
		self.size = f.size
		self.timestamp = f.timestamp

class IVFDemuxer:
	def __init__(self):
		self.stream = None
		self.pos = 0

	def setup(self, path):
		self.pos = 0
		self.stream = open(path, "rb").read()
		h = IVFHeader.parse(self.stream[:32])
		self.pos += 32
		print("[IVF] codec: %s %dx%d frames: %d" % (h.fourcc, h.width, h.height, h.frame_count))
		self.header = h
		if (h.fourcc == "VP90"):
			return AVD_MODE_VP9
		if (h.fourcc == "AV01"):
			return AVD_MODE_AV1
		raise ValueError("unsupported fourcc (%s)" % (h.fourcc))

	def read_all(self, path):
		mode = self.setup(path)
		slices = []
		for n in range(self.header.frame_count):
			slices.append(self.read_frame())
		return slices

	def read_frame(self):
		f = IVFFrameHeader.parse(self.stream[self.pos:self.pos+12])
		self.pos += 12
		b = self.stream[self.pos:self.pos+f.size]
		self.pos += f.size
		return IVFFrame(f, b)

class AVDVP9Slice(AVDSlice):
	def __init__(self):
		super().__init__()
		self.mode = "vp09"

	def __repr__(self):
		s = "\n[slice: %d key_frame: %d]\n" % (self.idx, not self.frame_type)
		s += self.show_entries()
		return s

	def get_payload(self):
		return self.payload.payload

class AVDVP9Parser(AVDParser):
	def __init__(self):
		super().__init__("devp9", "")
		self.arr_keys = [
			("ref_frame_idx", VP9_REF_FRAMES),
			("ref_frame_sign_bias", VP9_REF_FRAMES),
			("loop_filter_ref_deltas", VP9_MAX_REF_LF_DELTAS),
			("loop_filter_mode_deltas", VP9_MAX_MODE_LF_DELTAS),
		]
		self.slccls = AVDVP9Slice
		self.reader = IVFDemuxer()

	def parse(self, path):
		headers = self.get_headers(path)
		slices = self.reader.read_all(path)
		assert(len(headers) <= len(slices))
		for i,hdr in enumerate(headers):
			hdr.payload = slices[i]
		return headers
