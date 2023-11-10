#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..parser import *
from .probs import *
from .types import *

import ctypes
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

class IVFDemuxer:
	def __init__(self):
		self.stream = None
		self.pos = 0

	def read_header(self, path):
		self.pos = 0
		self.stream = open(path, "rb").read()
		h = IVFHeader.parse(self.stream[:32])
		self.header = h
		print("[IVF] codec: %s %dx%d frames: %d" % (h.fourcc, h.width, h.height, h.frame_count))
		self.pos += 32
		return h

	def read_mode(self, path):
		h = self.read_header(path)
		if (h.fourcc == "VP90"):
			return "vp09"
		if (h.fourcc == "AV01"):
			return "av01"
		raise ValueError("unsupported fourcc (%s)" % (h.fourcc))

	def read_all(self, path):
		self.read_header(path)
		slices = []
		for n in range(self.header.frame_count):
			slices.append(self.read_frame())
		return slices

	def read_frame(self):
		f = IVFFrameHeader.parse(self.stream[self.pos:self.pos+12])
		self.pos += 12
		b = self.stream[self.pos:self.pos+f.size]
		self.pos += f.size
		return AVDFrame(b, f.size, f.timestamp)

class AVDVP9Slice(AVDSlice):
	def __init__(self):
		super().__init__()
		self.mode = "vp09"
		self._banned_keys = ["idx", "frame", "probs", "probs_data"]

	def __repr__(self):
		s = "\n[slice: %d key_frame: %d]\n" % (self.idx, not self.frame_type)
		s += self.show_entries()
		return s

	def get_payload(self):
		return self.frame.payload

	def get_probs(self):
		return self.probs_data

class AVDVP9Parser(AVDParser):
	def __init__(self):
		super().__init__(lib_path="libvp9.so")
		self.lib.libvp9_init.restype = ctypes.c_void_p
		self.lib.libvp9_free.argtypes = [ctypes.c_void_p]
		self.lib.libvp9_decode.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]

		self.arr_keys = [
			("ref_frame_idx", VP9_REF_FRAMES),
			("ref_frame_sign_bias", VP9_REF_FRAMES),
			("loop_filter_ref_deltas", VP9_MAX_REF_LF_DELTAS),
			("loop_filter_mode_deltas", VP9_MAX_MODE_LF_DELTAS),
		]
		self.slccls = AVDVP9Slice
		self.reader = IVFDemuxer()

	def parse(self, path, num=0):
		header = self.reader.read_header(path)

		handle = self.lib.libvp9_init()
		if (handle == None):
			raise RuntimeError("Failed to init libvp9")

		with pipes() as (out, err):
			frames_all = []
			probs_all = []
			for i in range(header.frame_count):
				frame = self.reader.read_frame()
				err = self.lib.libvp9_decode(handle, frame.payload, frame.size)
				probs = ctypes.string_at(handle, LibVP9Probs.sizeof()) # not great but it works
				frames_all.append(frame)
				probs_all.append(probs)
				if (num and (i == num)):
					break
		stdout = out.read()
		self.lib.libvp9_free(handle)

		headers = self.parse_headers(stdout)
		assert(len(headers) == len(frames_all) == len(probs_all))
		for i,hdr in enumerate(headers):
			hdr.frame = frames_all[i]
			hdr.probs = LibVP9Probs.parse(probs_all[i])
			hdr.probs_data = hdr.probs.to_avdprobs(hdr.probs)
		return headers
