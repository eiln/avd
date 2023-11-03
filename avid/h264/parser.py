#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..utils import dotdict
from .types import *

import ctypes
import subprocess
from math import ceil
from pathlib import Path

class AVDH264Slice(dotdict):
	def __repr__(self):
		s = "slice: nal_unit_type: %d\n" % (self.nal_unit_type)
		for key in list(self.keys()):
			if (key in ["payload", "nal_unit_type"]): continue
			val = self[key]
			if (isinstance(val, int) or isinstance(val, float)):
				s += "\t%s: %d\n" % (key, val)
			elif (isinstance(val, list)):
				s += "\t%s: [%s]\n" % (key, ", ".join([str(v) for v in val]))
		return s

	def get_payload(self):
		def transform(dat): # match macOS
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

class AVDH264Parser:
	def __init__(self):
		self.bin_path = (Path(__file__).parent / '../../codecs/deh264').resolve()
		lib_path = (Path(__file__).parent / '../../codecs/libh264.so').resolve()
		self.lib = ctypes.cdll.LoadLibrary(lib_path)

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

		# I know this sucks but it's just not possible to write cpython
		# bindings for a stream parser. This also makes N/A fields explicit
		res = subprocess.check_output([f'{self.bin_path}', path], text=True)

		lines = res.splitlines()
		start = [i for i,line in enumerate(lines) if "{" in line]
		end = [i for i,line in enumerate(lines) if "}" in line]
		assert(len(start) == len(end))

		slice_idx = 0
		sps_count = 0
		pps_count = 0
		sps_list = [None] * AVD_H264_MAX_SPS
		pps_list = [None] * AVD_H264_MAX_PPS
		slices = []
		for i,(start, end) in enumerate(list(zip(start, end))):
			group = lines[start:end]

			unit = AVDH264Slice()
			unit.idx = i

			content = group[:]
			content = [line.strip() for line in content if (line.startswith("\t")) and ("=" in line)]
			for kv in content:
				key = kv.split()[0].split("[", 1)[0]
				val = kv.split()[2]
				val = float(val) if '.' in val else int(val)
				arr_keys = ["modification_of_pic_nums_idc_l0", "modification_of_pic_nums_idc_l1", "abs_diff_pic_num_minus1_l0", "abs_diff_pic_num_minus1_l1", "mmco_forget_short", "mmco_short_to_long", "mmco_forget_long", "mmco_this_to_long", "mmco_forget_long_max"]
				if any(a in key for a in arr_keys):
					for a in arr_keys:
						if (a in key):
							if a not in unit:
								unit[a] = [val]
							else:
								unit[a].append(val)
				else:
					key = kv.split()[0].replace("[", "_").replace("]", "_").replace("__", "_").rstrip("_")
					if ((key in unit)):
						unit[key] = [unit[key]] if not isinstance(unit[key], list) else unit[key]
						unit[key].append(val)
					else:
						unit[key] = val

			if (unit.nal_unit_type == H264_NAL_SEI): continue
			unit.payload = payloads[i]

			if (unit.nal_unit_type == H264_NAL_SPS):
				assert(unit.seq_parameter_set_id < AVD_H264_MAX_SPS)
				sps_list[unit.seq_parameter_set_id] = unit
				sps_count += 1
			elif (unit.nal_unit_type == H264_NAL_PPS):
				assert(unit.pic_parameter_set_id < AVD_H264_MAX_PPS)
				pps_list[unit.pic_parameter_set_id] = unit
				pps_count += 1
			else:
				slices.append(unit)

		return sps_list, pps_list, slices
