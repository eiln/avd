#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..parser import AVDParser, AVDSlice
from ..types import *
from .types import *

import ctypes
from math import ceil

class AVDH264Slice(AVDSlice):
	def __init__(self):
		super().__init__()
		self._banned_keys = ["payload", "nal_unit_type", "idx"]
		self._reprwidth = 38
		self.mode = "h264"

	def __repr__(self):
		s = "\n[slice: %d nal_unit_type: %d]\n" % (self.idx, self.nal_unit_type)
		s += self.show_entries()
		return s

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
		return ceil(self.header_size / 8) + 4

	def get_payload_size(self):
		return len(self.get_payload()) - self.get_payload_offset()

class AVDH264Parser(AVDParser):
	def __init__(self):
		super().__init__("deh264", "libh264.so")
		self.arr_keys = [("modification_of_pic_nums_idc_l0", H264_MAX_REFS),
				("modification_of_pic_nums_idc_l1", H264_MAX_REFS),
				("abs_diff_pic_num_minus1_l0", H264_MAX_REFS),
				("abs_diff_pic_num_minus1_l1", H264_MAX_REFS),
				("mmco_forget_short", H264_MAX_MMCO_COUNT),
				("mmco_short_to_long", H264_MAX_MMCO_COUNT),
				("mmco_forget_long", H264_MAX_MMCO_COUNT),
				("mmco_this_to_long", H264_MAX_MMCO_COUNT),
				("mmco_forget_long_max", H264_MAX_MMCO_COUNT),
		]
		self.slccls = AVDH264Slice

	def get_payloads(self, path):
		buf = open(path, "rb").read()
		bufpos = 0
		bytesnum = len(buf)
		nal_start = ctypes.c_int()
		nal_end = ctypes.c_int()
		nalus = []
		while (bytesnum > 0):
			err = self.lib.libh264_find_nal_unit(buf[bufpos:], bytesnum, ctypes.byref(nal_start), ctypes.byref(nal_end))
			payload = buf[bufpos:bufpos+nal_end.value]
			nalus.append(payload)
			bufpos += nal_start.value
			# /* RBSP */
			bufpos += (nal_end.value - nal_start.value)
			bytesnum -= nal_end.value
		return nalus

	def parse(self, path):
		payloads = self.get_payloads(path)
		units = self.get_headers(path)

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
			else:
				slices.append(unit)
				slice_idx += 1
		return sps_list, pps_list, slices
