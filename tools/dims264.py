#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import os

from avid.h264.fp import *
from avid.utils import *
from tools.common import *

def ca(x, y, msg=""): return cassert(x, y, msg=msg, fatal=False)

def test(ctx):
	# e.g. 128 x 64 8-bit 4:2:0
	# 0x004000: instruction FIFO x 6
	# 0x720000: SPS/PPS (not used by hardware)
	# 0x734000: rvra0_addr
	# 0x73c100: y_addr: rvra0_addr + rvra_size + 0x100
	# 0x73e100: uv_addr: y_addr + (height * width)
	# 0x744000: slice_data_addr: round_up(uv_addr + (width * height // 2), 0x4000) + 0x4000
	# 0x74c000: sps_tile_addr: slice_data_addr + slice_data_size
	# 0x80c000: pps_tile_base_addr: sps_tile_addr + (sps_tile_size * sps_tile_count)
	# 0x834000: rvra1_addr: pps_tile_base_addr + (pps_tile_size * pps_tile_count)
	ca(ctx.rvra0_addr, 0x734000)

	w = ctx.width
	h = ctx.height
	print(ctx.dirname)

	stride = 2 if ctx.is_10bit else 1
	in_width = round_up(ctx.width * stride, 64)
	in_height = round_up(ctx.height, 16)
	luma_size = in_width * in_height
	ca(ctx.uv_addr, ctx.y_addr + luma_size, msg="uv_addr")
	ca(ctx.stride, in_width >> 4, msg="stride")
	#print(ctx.width, ctx.height, ctx.stride, ctx.is_422)

	w2 = round_up(ctx.width * stride, 64)
	h2 = round_up(ctx.height, 16)
	chroma_size = (w2 * h2)
	if (not ctx.is_422):
		chroma_size //= 2
	#print(hex(ctx.uv_addr + chroma_size))
	#ca(ctx.slice_data_addr, round_up(round_up(ctx.uv_addr, 0x100) + chroma_size, 0x4000) + 0x4000, msg="slice_data_addr")

	ca(ctx.sps_tile_count, 24)
	ca(ctx.pps_tile_size, 0x8000)

	s = (w - 1) * (h - 1) // 0x10000
	ca(s, (ctx.sps_tile_size // 0x4000) - 2)
	ca(ctx.sps_tile_size, (((w - 1) * (h - 1) // 0x10000) + 2) * 0x4000)

	ca(ctx.sps_tile_addr, (ctx.slice_data_addr + ctx.slice_data_size), msg="sps_tile_addr")
	ca(ctx.pps_tile_addr, (ctx.sps_tile_addr + (ctx.sps_tile_size * ctx.sps_tile_count)))
	x = 0
	if (in_width > 2048):
		x = 0x4000
	ca(ctx.rvra1_addr, (ctx.pps_tile_addr + (ctx.pps_tile_size * 5) + x), msg="rvra1_addr")

	width_mbs = (ctx.width + 15) // 16
	height_mbs = (ctx.height + 15) // 16
	#x = (396 // (height_mbs * width_mbs)) # DPB
	#print(ctx.rvra_count, x, hex((1024 * 396) // (ctx.rvra_count + 1)), hex(ctx.rvra_size3))

	ws = round_up(ctx.width, 32)
	hs = round_up(ctx.height, 32)
	ca(ctx.rvra_size0, (hs * ws) + ((hs * ws) // 4)) # luma
	size2 = ctx.rvra_size0
	size3 = size2
	if (not ctx.is_422):
		size3 = size2 // 2
	if (ctx.is_422 and ctx.is_10bit):
		size3 = round(ctx.height * ctx.width * 1.25)
		size3 = round_up(size3, 0x100)
	size2 = round(size3)
	ca(ctx.rvra_size2, size2, msg="rvra_size2")
	y = max(nextpow2(ctx.width) * nextpow2(ctx.height) // 32, 0x100)
	ca(ctx.rvra_size1, y, msg="rvra_size1")
	assert(isdiv(ctx.rvra_size, 0x4000))
	size = ctx.rvra_size0 + ctx.rvra_size1 + ctx.rvra_size2
	delta = ctx.rvra_size - round_up(size, 0x4000)
	assert(isdiv(delta, 0x4000))
	delta = delta // 0x4000

	size = (ctx.width) * (ctx.height)
	d = 1
	if (size >= 0x50 and size <= 0x80):
		d = 2
	if (size >= 0x1fe):
		d = 3
	"""
	if (ctx.width >= 1024):
		d2 = 2
	if (ctx.width >= 1800):
		d2 = 3
	if (ctx.width >= 3800):
		d2 = 9
	"""
	#ca(delta, d, "delta")
	#print(f"{str(w).rjust(4)} {str(h).rjust(4)} {str(delta)} {str(hex(size))}")
	#print(delta)

	w = round_up(ctx.width, 32)
	h = round_up(ctx.height, 32)
	d = min((((w - 1) * (h - 1) // 0x8000) + 2), 0xff)
	#ca(ctx.slice_data_size // 0x4000, d)
	#ca(ctx.slice_data_size, min((((w - 1) * (h - 1) // 0x8000) + 2), 0xff) * 0x4000)

def main(dirname):
	paths = os.listdir(dirname)
	paths = sorted([os.path.join(dirname, path) for path in paths if "frame" in path])[:32]

	fp0 = AVDH264V3FrameParams.parse(open(paths[0], "rb").read())
	fp1 = AVDH264V3FrameParams.parse(open(paths[1], "rb").read())
	fp2 = AVDH264V3FrameParams.parse(open(paths[2], "rb").read())

	ctx = dotdict()
	ctx.dirname = dirname
	ctx.width = (fp0.hdr.hdr_3c_height_width & 0xffff) + 1
	ctx.height = (fp0.hdr.hdr_3c_height_width >> 16) + 1
	ctx.stride = int(fp0.hdr.hdr_218_width_align)
	cassert(fp0.hdr.hdr_218_width_align, fp0.hdr.hdr_21c_width_align)

	ctx.y_addr = fp0.hdr.hdr_210_y_addr_lsb8 << 8
	ctx.uv_addr = fp0.hdr.hdr_214_uv_addr_lsb8 << 8

	ctx.slice_data_addr = fp0.slc.slc_a84_slice_addr_low & 0xffffff00
	ctx.slice_data_size = (fp0.hdr.hdr_bc_sps_tile_addr_lsb8 << 8) - ctx.slice_data_addr

	ctx.sps_tile_addr = fp0.hdr.hdr_bc_sps_tile_addr_lsb8 << 8
	ctx.sps_tile_size = (fp1.hdr.hdr_bc_sps_tile_addr_lsb8 - fp0.hdr.hdr_bc_sps_tile_addr_lsb8) << 8
	ctx.pps_tile_addr = fp0.hdr.hdr_9c_pps_tile_addr_lsb8[0] << 8
	ctx.pps_tile_size = (fp0.hdr.hdr_9c_pps_tile_addr_lsb8[1] - fp0.hdr.hdr_9c_pps_tile_addr_lsb8[0]) << 8

	ctx.rvra0_addr = fp0.hdr.hdr_c0_curr_ref_addr_lsb7[1] << 7
	ctx.rvra1_addr = fp1.hdr.hdr_c0_curr_ref_addr_lsb7[1] << 7

	ctx.rvra_size0 = (fp1.hdr.hdr_c0_curr_ref_addr_lsb7[0] - fp1.hdr.hdr_c0_curr_ref_addr_lsb7[1]) << 7
	ctx.rvra_size1 = (fp1.hdr.hdr_c0_curr_ref_addr_lsb7[3] - fp1.hdr.hdr_c0_curr_ref_addr_lsb7[0]) << 7
	ctx.rvra_size2 = (fp1.hdr.hdr_c0_curr_ref_addr_lsb7[2] - fp1.hdr.hdr_c0_curr_ref_addr_lsb7[3]) << 7
	#ctx.rvra_size3 = ((fp2.hdr.hdr_c0_curr_ref_addr_lsb7[0] - fp1.hdr.hdr_c0_curr_ref_addr_lsb7[0]) << 7) - ctx.rvra_size2 - ctx.rvra_size1 - ctx.rvra_size0
	#ctx.rvra_total_size = (fp2.hdr.hdr_c0_curr_ref_addr_lsb7[0] - fp1.hdr.hdr_c0_curr_ref_addr_lsb7[0]) << 7
	ca((fp0.hdr.hdr_c0_curr_ref_addr_lsb7[0] << 7), (ctx.rvra0_addr + ctx.rvra_size0))
	ca((fp0.hdr.hdr_c0_curr_ref_addr_lsb7[3] << 7), (ctx.rvra0_addr + ctx.rvra_size0 + ctx.rvra_size1))
	ca((fp0.hdr.hdr_c0_curr_ref_addr_lsb7[2] << 7), (ctx.rvra0_addr + ctx.rvra_size0 + ctx.rvra_size1 + ctx.rvra_size2))
	#ca(ctx.rvra_total_size, (ctx.rvra_size0 + ctx.rvra_size1 + ctx.rvra_size2 + ctx.rvra_size3))

	rvras = []
	sps_tile_count = 0
	for i,path in enumerate(paths):
		fp = AVDH264V3FrameParams.parse(open(path, "rb").read())
		addr = fp.hdr.hdr_c0_curr_ref_addr_lsb7[1] << 7
		rvras.append(addr)

		addr = fp.hdr.hdr_bc_sps_tile_addr_lsb8 << 8
		if ((i) and (not sps_tile_count) and (addr == ctx.sps_tile_addr)):
			sps_tile_count = i
			ctx.sps_tile_count = i

	rvras = sorted(list(set(rvras)))
	assert(rvras[0] == 0x734000)
	assert(rvras[1] == (ctx.rvra1_addr))
	ctx.rvra_size = ctx.y_addr - ctx.rvra0_addr - 0x100
	ctx.rvra_size3 = ctx.rvra_size - ctx.rvra_size0 - ctx.rvra_size1 - ctx.rvra_size2
	ctx.is_422 = int(fp0.hdr.hdr_2c_sps_param & (2 << 24) == (2 << 24))
	ctx.is_10bit = int("10b" in ctx.dirname)
	test(ctx)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='dim calc experiment')
	parser.add_argument('-d','--dir', type=str, default="../data/h264", help="trace dir name")
	parser.add_argument('-nf','--non-fatal', action='store_true', help="non fatal")
	args = parser.parse_args()

	all_dirs = [os.path.join(args.dir, t) for t in os.listdir(os.path.join(args.dir))]
	all_dirs = [y for y in all_dirs if os.path.isdir(y)]
	all_dirs = sorted(all_dirs)
	for x in all_dirs:
		main(x)
