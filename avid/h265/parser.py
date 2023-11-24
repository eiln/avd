#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..parser import *
from .types import *

import ctypes
import subprocess
from math import ceil

class AVDH265Slice(AVDSlice):
	def __init__(self):
		super().__init__()
		self._banned_keys = ["payload", "nal_unit_type", "idx"]
		self._reprwidth = 39
		self.mode = "h265"

	def __repr__(self):
		s = "\n[slice: %d nal_unit_type: %d intra: %d" % (self.idx, self.nal_unit_type, IS_INTRA(self))
		if (IS_SLICE(self)):
			s += " slice_type: %s" % (self.get_slice_str(self.slice_type))
		s += "]\n"
		s += self.show_entries()
		return s

	def get_slice_str(self, t):
		if (t == HEVC_SLICE_I): return "I"
		if (t == HEVC_SLICE_P): return "P"
		if (t == HEVC_SLICE_B): return "B"
		return "?"

	def get_payload(self):
		def transform(dat): # match macOS behavior
			new = b'\x00' + dat
			return new[:2] + b'\x00.' + new[4:]
		payload = transform(self.payload)
		if (IS_INTRA(self)):
			start = 0
		else:
			start = 1
		return payload[start:]

	def get_payload_offset(self):
		return (self.slice_header_size // 8) + 1 + 4

	def get_payload_size(self):
		return len(self.get_payload()) - self.get_payload_offset()

class AVDH265Parser(AVDParser):
	def __init__(self):
		super().__init__(lib_path="libh265.so")
		self.lib.libh265_init.restype = ctypes.c_void_p
		self.lib.libh265_free.argtypes = [ctypes.c_void_p]
		self.lib.libh265_decode.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
					ctypes.c_int, ctypes.POINTER(ctypes.c_int),
					ctypes.POINTER(ctypes.c_int)]
		self.arr_keys = [
			("luma_weight_l0_flag", HEVC_MAX_REFS),
			("luma_weight_l0", HEVC_MAX_REFS),
			("luma_offset_l0", HEVC_MAX_REFS),
			("luma_weight_l1_flag", HEVC_MAX_REFS),
			("luma_weight_l1", HEVC_MAX_REFS),
			("luma_offset_l1", HEVC_MAX_REFS),
			("chroma_weight_l0_flag", HEVC_MAX_REFS),
			("chroma_weight_l0", (HEVC_MAX_REFS, 2)),
			("chroma_offset_l0", (HEVC_MAX_REFS, 2)),
			("chroma_weight_l1_flag", HEVC_MAX_REFS),
			("chroma_weight_l1", (HEVC_MAX_REFS, 2)),
			("chroma_offset_l1", (HEVC_MAX_REFS, 2)),
		]
		self.slccls = AVDH265Slice

	def parse_payloads(self, path, num=0):
		buf = open(path, "rb").read()
		bufpos = 0
		bytesnum = len(buf)
		nal_start = ctypes.c_int()
		nal_end = ctypes.c_int()

		handle = self.lib.libh265_init()
		if (handle == None):
			raise RuntimeError("Failed to init libh265")

		with pipes() as (out, err):
			nalus = []
			while (bytesnum > 0):
				if ((num) and (len(nalus) >= num)) and 0:
					break
				self.lib.libh265_decode(handle, buf[bufpos:], bytesnum, ctypes.byref(nal_start), ctypes.byref(nal_end))
				payload = buf[bufpos:bufpos+nal_end.value]
				nalus.append(payload)
				bufpos += nal_end.value
				bytesnum -= nal_end.value
		stdout = out.read()

		self.lib.libh265_free(handle)
		return nalus, stdout

	def parse(self, path, num=0):
		payloads, stdout = self.parse_payloads(path, num=num)
		units = self.parse_headers(stdout)

		slice_idx = 0
		vps_list = [None] * HEVC_MAX_VPS_COUNT
		sps_list = [None] * HEVC_MAX_SPS_COUNT
		pps_list = [None] * HEVC_MAX_PPS_COUNT
		slices = []
		for i,unit in enumerate(units):
			unit.idx = slice_idx
			unit.payload = payloads[i]

			if (unit.nal_unit_type == HEVC_NAL_VPS):
				assert(unit.vps_video_parameter_set_id < HEVC_MAX_VPS_COUNT)
				unit.idx = unit.vps_video_parameter_set_id
				vps_list[unit.vps_video_parameter_set_id] = unit
			elif (unit.nal_unit_type == HEVC_NAL_SPS):
				assert(unit.sps_seq_parameter_set_id < HEVC_MAX_SPS_COUNT)
				unit.idx = unit.sps_seq_parameter_set_id
				sps_list[unit.sps_seq_parameter_set_id] = unit
			elif (unit.nal_unit_type == HEVC_NAL_PPS):
				assert(unit.pps_pic_parameter_set_id < HEVC_MAX_PPS_COUNT)
				unit.idx = unit.pps_pic_parameter_set_id
				pps_list[unit.pps_pic_parameter_set_id] = unit
			elif (unit.nal_unit_type == HEVC_NAL_SEI_PREFIX or unit.nal_unit_type == HEVC_NAL_SEI_SUFFIX):
				continue
			elif (unit.nal_unit_type in [HEVC_NAL_TRAIL_R, HEVC_NAL_TRAIL_N, HEVC_NAL_TSA_N,HEVC_NAL_TSA_R, HEVC_NAL_STSA_N, HEVC_NAL_STSA_R, HEVC_NAL_BLA_W_LP, HEVC_NAL_BLA_W_RADL, HEVC_NAL_BLA_N_LP, HEVC_NAL_IDR_W_RADL, HEVC_NAL_IDR_N_LP, HEVC_NAL_CRA_NUT, HEVC_NAL_RADL_N, HEVC_NAL_RADL_R, HEVC_NAL_RASL_N, HEVC_NAL_RASL_R]):
				slices.append(unit)
				slice_idx += 1
			else:
				continue
		return vps_list, sps_list, pps_list, slices
