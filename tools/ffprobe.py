#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import os
import argparse
from construct import *
from avid.types import *

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

def det_ivf_format(path):
	b = open(path, "rb").read()[:32]
	d = IVFHeader.parse(b)
	print("[IVF] codec: %s %dx%d frames: %d" % (d.fourcc, d.width, d.height, d.frame_count))
	if (d.fourcc == "VP90"):
		return AVD_MODE_VP9
	if (d.fourcc == "AV01"):
		return AVD_MODE_AV1
	raise ValueError("unsupported fourcc (%s)" % (d.fourcc))

def det_format(path):
	fname, ext = os.path.splitext(path)
	if ext in [".h264", ".264"]:
		return AVD_MODE_H264
	if ext in [".h265", ".265"]:
		return AVD_MODE_H265
	if ext in [".ivf", "ivp9"]:
		return det_ivf_format(path)
	raise ValueError("unsupported format (%s)" % (ext))

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='ffprobe')
	parser.add_argument('input', type=str, help="path to bitstream")
	args = parser.parse_args()
	mode = det_format(args.input)

__all__ = ["det_format", "AVD_MODE_H264", "AVD_MODE_H265", "AVD_MODE_VP9", "AVD_MODE_AV1"]
