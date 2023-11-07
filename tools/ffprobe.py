#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import os
import argparse
from construct import *
from avid.types import *
from avid.vp9.parser import IVFDemuxer

def det_format(path):
	fname, ext = os.path.splitext(path)
	if ext in [".h264", ".264"]:
		return AVD_MODE_H264
	if ext in [".h265", ".265"]:
		return AVD_MODE_H265
	if ext in [".ivf", "ivp9"]:
		dmx = IVFDemuxer()
		return dmx.read_mode(path)
	raise ValueError("unsupported format (%s)" % (ext))

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='ffprobe')
	parser.add_argument('input', type=str, help="path to bitstream")
	args = parser.parse_args()
	mode = det_format(args.input)

__all__ = ["det_format", "AVD_MODE_H264", "AVD_MODE_H265", "AVD_MODE_VP9", "AVD_MODE_AV1"]
