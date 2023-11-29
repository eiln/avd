#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..parser import *
from .types import *

import ctypes
import subprocess
from math import ceil

class AVDH264Slice(AVDSlice):
	def __init__(self):
		super().__init__()
		self._banned_keys = ["payload", "nal_unit_type", "idx"]
		self._reprwidth = 38
		self.mode = "h264"

	def show_slice_header(self):
		s = "\n[slice: %d nal_unit_type: %d" % (self.idx, self.nal_unit_type)
		if (IS_SLICE(self)):
			s += " slice_type: %s" % (self.get_slice_str(self.slice_type))
		s += "]\n"
		return s

	def get_slice_str(self, t):
		if (t == H264_SLICE_TYPE_I): return "I"
		if (t == H264_SLICE_TYPE_P): return "P"
		if (t == H264_SLICE_TYPE_B): return "B"
		return "?"

	def get_payload(self):
		def transform(dat): # match macOS behavior
			new = b'\x00' + dat
			return new[:2] + b'\x00.' + new[4:]
		payload = transform(self.payload)
		if (self.nal_unit_type == H264_NAL_SLICE_IDR):
			start = 0
		else:
			start = 1
		return payload[start:]

	def get_payload_offset(self):
		return ceil(self.slice_header_size / 8) + 4

	def get_payload_size(self):
		return len(self.get_payload()) - self.get_payload_offset()

class AVDH264Parser(AVDParser):
	def __init__(self):
		super().__init__(lib_path="libh264.so")
		self.lib.libh264_init.restype = ctypes.c_void_p
		self.lib.libh264_free.argtypes = [ctypes.c_void_p]
		self.lib.libh264_decode.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
					ctypes.c_int, ctypes.POINTER(ctypes.c_int),
					ctypes.POINTER(ctypes.c_int)]

		self.arr_keys = [("modification_of_pic_nums_idc_l0", H264_MAX_REFS),
				("modification_of_pic_nums_idc_l1", H264_MAX_REFS),
				("abs_diff_pic_num_minus1_l0", H264_MAX_REFS),
				("abs_diff_pic_num_minus1_l1", H264_MAX_REFS),

				("memory_management_control_operation", H264_MAX_MMCO_COUNT),
				("mmco_short_args", H264_MAX_MMCO_COUNT),
				("mmco_long_args", H264_MAX_MMCO_COUNT),

				("luma_weight_l0_flag", H264_MAX_REFS),
				("luma_weight_l0", H264_MAX_REFS),
				("luma_offset_l0", H264_MAX_REFS),
				("luma_weight_l1_flag", H264_MAX_REFS),
				("luma_weight_l1", H264_MAX_REFS),
				("luma_offset_l1", H264_MAX_REFS),

				("chroma_weight_l0_flag", H264_MAX_REFS),
				("chroma_weight_l0", (H264_MAX_REFS, 2)),
				("chroma_offset_l0", (H264_MAX_REFS, 2)),
				("chroma_weight_l1_flag", H264_MAX_REFS),
				("chroma_weight_l1", (H264_MAX_REFS, 2)),
				("chroma_offset_l1", (H264_MAX_REFS, 2)),
		]
		self.slccls = AVDH264Slice

	def parse_payloads(self, path, num=0):
		buf = open(path, "rb").read()
		bufpos = 0
		bytesnum = len(buf)
		nal_start = ctypes.c_int()
		nal_end = ctypes.c_int()

		handle = self.lib.libh264_init()
		if (handle == None):
			raise RuntimeError("Failed to init libh264")

		with pipes() as (out, err):
			nalus = []
			while (bytesnum > 0):
				if ((num) and (len(nalus) >= num)) and 0:
					break
				self.lib.libh264_decode(handle, buf[bufpos:], bytesnum, ctypes.byref(nal_start), ctypes.byref(nal_end))
				payload = buf[bufpos:bufpos+nal_end.value]
				nalus.append(payload)
				bufpos += nal_end.value
				bytesnum -= nal_end.value
		stdout = out.read()

		self.lib.libh264_free(handle)
		return nalus, stdout

	def parse(self, path, num=0):
		payloads, stdout = self.parse_payloads(path, num=num)
		units = self.parse_headers(stdout)

		slice_idx = 0
		sps_list = [None] * H264_MAX_SPS_COUNT
		pps_list = [None] * H264_MAX_PPS_COUNT
		slices = []
		for i,unit in enumerate(units):
			if (unit.nal_unit_type == H264_NAL_SEI): continue
			unit.idx = slice_idx
			unit.payload = payloads[i]

			if (unit.nal_unit_type == H264_NAL_SPS):
				assert(unit.seq_parameter_set_id < H264_MAX_SPS_COUNT)
				unit.idx = unit.seq_parameter_set_id
				sps_list[unit.seq_parameter_set_id] = unit
			elif (unit.nal_unit_type == H264_NAL_PPS):
				assert(unit.pic_parameter_set_id < H264_MAX_PPS_COUNT)
				unit.idx = unit.pic_parameter_set_id
				pps_list[unit.pic_parameter_set_id] = unit
			elif (unit.nal_unit_type in [H264_NAL_SLICE_NONIDR, H264_NAL_SLICE_PART_A, H264_NAL_SLICE_PART_B, H264_NAL_SLICE_PART_C, H264_NAL_SLICE_IDR, H264_NAL_SLICE_AUX, H264_NAL_SLICE_EXT]):
				slices.append(unit)
				slice_idx += 1
			else:
				self.log("skipping unknown NAL type (%d)" % unit.nal_unit_type)
		return sps_list, pps_list, slices
