#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

import ctypes
import os
import struct
import subprocess
import sys
import threading
import time
from collections import namedtuple
from pathlib import Path
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

	def __repr__(self):
		s = "\n[slice: %d]\n" % (self.idx)
		s += self.show_entries()
		return s

class OutputGrabber(object):
	# https://stackoverflow.com/a/29834357
	escape_char = "\b"

	def __init__(self, stream=None, threaded=False):
		self.origstream = stream
		self.threaded = threaded
		if self.origstream is None:
			self.origstream = sys.stdout
		self.origstreamfd = self.origstream.fileno()
		self.capturedtext = ""
		# Create a pipe so the stream can be captured:
		self.pipe_out, self.pipe_in = os.pipe()

	def __enter__(self):
		self.start()
		return self

	def __exit__(self, type, value, traceback):
		self.stop()

	def start(self):
		self.capturedtext = ""
		# Save a copy of the stream:
		self.streamfd = os.dup(self.origstreamfd)
		# Replace the original stream with our write pipe:
		os.dup2(self.pipe_in, self.origstreamfd)
		if self.threaded:
			# Start thread that will read the stream:
			self.workerThread = threading.Thread(target=self.readOutput)
			self.workerThread.start()
			# Make sure that the thread is running and os.read() has executed:
			time.sleep(0.01)

	def stop(self):
		"""
		Stop capturing the stream data and save the text in `capturedtext`.
		"""
		# Print the escape character to make the readOutput method stop:
		self.origstream.write(self.escape_char)
		# Flush the stream to make sure all our data goes in before
		# the escape character:
		self.origstream.flush()
		if self.threaded:
			# wait until the thread finishes so we are sure that
			# we have until the last character:
			self.workerThread.join()
		else:
			self.readOutput()
		# Close the pipe:
		os.close(self.pipe_in)
		os.close(self.pipe_out)
		# Restore the original stream:
		os.dup2(self.streamfd, self.origstreamfd)
		# Close the duplicate stream:
		os.close(self.streamfd)

	def readOutput(self):
		"""
		Read the stream data (one byte at a time)
		and save the text in `capturedtext`.
		"""
		while True:
			char = os.read(self.pipe_out,1).decode(self.origstream.encoding)
			if not char or self.escape_char in char:
				break
			self.capturedtext += char

class AVDParser:
	def __init__(self, bin_path, lib_path):
		self.bin_path = (Path(__file__).parent / ('../codecs/%s' % (bin_path))).resolve()
		if (lib_path):
			lib_path = (Path(__file__).parent / ('../codecs/%s' % (lib_path))).resolve()
			self.lib = ctypes.cdll.LoadLibrary(lib_path)
		self.arr_keys = []
		self.slccls = AVDSlice

	def parse_headers(self, stdout):
		# I know this sucks but it's just not possible to write cpython
		# bindings for a stream parser. This also makes N/A fields explicit
		#res = subprocess.check_output([f'{self.bin_path}', path], text=True)

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

__all__ = ["AVDParser", "OutputGrabber", "AVDSlice", "AVDFrame"]
