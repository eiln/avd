#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

import ctypes
import struct
from collections import namedtuple
from pathlib import Path
from wurlitzer import pipes
from .utils import dotdict

class AVDFrame(namedtuple('AVDFrame', ['payload', 'size', 'timestamp'])):
	def __repr__(self):
		word = struct.unpack("<I", self.payload[:4])[0]
		return "[frame: size: %d timestamp: %d word: 0x%x]" % (self.size, self.timestamp, word)

class AVDSlice(dotdict):
	def __init__(self):
		self._banned_keys = ["idx", "frame"]
		self._reprwidth = 36

	def show_list_entry(self, key, val):
		s = ""
		for i,v in enumerate(val):
			if (v != None):
				kr = ("\t%s[%d]" % (key, i)).ljust(self._reprwidth)
				s += "%s %d\n" % (kr, v)
		return s

	def show_entries(self):
		s = ""
		for key in list(self.keys()):
			if ((key.startswith("_")) or (key in self._banned_keys)): continue
			val = self[key]
			if (isinstance(val, int) or isinstance(val, float)):
				kr = ("\t%s" % (key)).ljust(self._reprwidth)
				s += "%s %d\n" % (kr, val)
			elif (isinstance(val, list)):
				s += self.show_list_entry(key, val)
		return s

	def show_slice_header(self):
		return "\n[slice: %d]\n" % (self.idx)

	def __repr__(self):
		s = self.show_slice_header()
		s += self.show_entries()
		return s

class AVDParser:
	def __init__(self, lib_path):
		if (lib_path):
			lib_path = (Path(__file__).parent / ('../codecs/%s' % (lib_path))).resolve()
			self.lib = ctypes.cdll.LoadLibrary(lib_path)
		self.arr_keys = []
		self.slccls = AVDSlice

	def parse_headers(self, stdout):
		# Yes we capture header fields from C-level stdout. This avoids the
		# stupidity of ctypes "structures" and explicitly marks N/A fields.
		lines = stdout.splitlines()
		start = [i for i,line in enumerate(lines) if "{" in line]
		end = [i for i,line in enumerate(lines) if "}" in line]
		assert(len(start) == len(end))

		units = []
		for i,(start, end) in enumerate(list(zip(start, end))):
			group = lines[start:end]

			unit = self.slccls()
			unit.idx = i

			content = group[:]
			content = [line.strip() for line in content if (line.startswith("\t")) and ("=" in line)]
			for kv in content:
				key = kv.split()[0].split("[", 1)[0]
				val = kv.split()[2]
				val = float(val) if '.' in val else int(val)
				if ((key in unit) and (isinstance(unit[key], list))):
					i = int(kv.split()[0].split("[")[1].split("]")[0])
					unit[key][i] = val
					continue

				if any(a[0] in key for a in self.arr_keys):
					for a in self.arr_keys:
						if (a[0] in key):
							nm, cnt = a
							i = int(kv.split()[0].split("[")[1].split("]")[0])
							if nm not in unit:
								unit[nm] = [None] * cnt
								unit[nm][i] = val
							else:
								unit[nm][i] = val
				elif (1 == 0):
					key = kv.split()[0].replace("[", "_").replace("]", "_").replace("__", "_").rstrip("_")
					if ((key in unit)):
						unit[key] = [unit[key]] if not isinstance(unit[key], list) else unit[key]
						unit[key].append(val)
					else:
						unit[key] = val
				else:
					unit[key] = val
			units.append(unit)

		return units

__all__ = ["AVDParser", "AVDSlice", "AVDFrame", "pipes"]
