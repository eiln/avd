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

def test(dims):
	# e.g. 128 x 64 8-bit 4:2:0
	# 0x004000: instruction FIFO x 6
	# 0x720000: SPS/PPS (not used by hardware)
	# 0x734000: rvra0_addr
	# 0x736800: rvra1_addr
	# 0x736900: rvra2_addr
	# 0x737d00: rvra3_addr
	# 0x73c100: y_addr: rvra0_addr + rvra_size + 0x100
	# 0x73e100: uv_addr: y_addr + (height * width)
	# 0x744000: slice_data_addr: round_up(uv_addr + (width * height // 2), 0x4000) + 0x4000
	# 0x74c000: sps_tile_addr: slice_data_addr + slice_data_size
	# 0x80c000: pps_tile_base_addr: sps_tile_addr + (sps_tile_size * sps_tile_count)
	# 0x834000: rvra1_addr: pps_tile_base_addr + (pps_tile_size * pps_tile_count)
	cassert(dims.rvra0_addr, 0x734000)
	cassert(dims.y_addr, (dims.rvra0_addr + dims.rvra_total_size + 0x100))

	scale = min(pow2div(dims.height), pow2div(dims.width))
	w = dims.width
	h = dims.height

	if (not(isdiv(dims.width, 32))):
		wr = round_up(dims.width, 64)
	else:
		wr = w
	hr = round_up(dims.height, 16)
	q = dims.uv_addr - (dims.y_addr - 0x100)
	d = (wr * hr) + 0x100
	#print(f"{str(w).rjust(4)} {str(h).rjust(4)} {str(hex(q)).rjust(4)} {str(hex(d)).rjust(4)}")
	cassert(q, d)
	cassert(dims.uv_addr, dims.y_addr + (wr * hr))

	q = dims.slice_data_addr - (dims.uv_addr - 0x100)
	d = (w * hr // 2) + 0x8000
	#print(f"{str(w).rjust(4)} {str(h).rjust(4)} {str(hex(q)).rjust(4)} {str(hex(d)).rjust(4)}")

	chroma_size = (wr * hr // 2)
	if (dims.height in [336, 4096]):
		chroma_size += 0x4000
	cassert(dims.slice_data_addr, round_up(dims.uv_addr + chroma_size, 0x4000) + 0x4000)

	cassert(dims.sps_tile_count, 24)
	cassert(dims.pps_tile_size, 0x8000)

	s = (w - 1) * (h - 1) // 0x10000
	cassert(s, (dims.sps_tile_size // 0x4000) - 2)
	cassert(dims.sps_tile_size, (((w - 1) * (h - 1) // 0x10000) + 2) * 0x4000)

	cassert(dims.sps_tile_addr, (dims.slice_data_addr + dims.slice_data_size))
	cassert(dims.pps_tile_addr, (dims.sps_tile_addr + (dims.sps_tile_size * dims.sps_tile_count)))
	#cassert(dims.rvra1_addr, (dims.pps_tile_addr + (dims.pps_tile_size * 5))) # const

	width_mbs = (dims.width + 15) // 16
	height_mbs = (dims.height + 15) // 16
	#x = (396 // (height_mbs * width_mbs)) # DPB
	#print(dims.rvra_count, x, hex((1024 * 396) // (dims.rvra_count + 1)), hex(dims.rvra_size3))

	ws = round_up(dims.width, 32)
	hs = round_up(dims.height, 32)
	cassert(dims.rvra_size0, (hs * ws) + ((hs * ws) // 4)) # luma
	cassert(dims.rvra_size2, (dims.rvra_size0 // 2))  # 4:2:0 chroma
	cassert(dims.rvra_size1, ((nextpow2(dims.height) // 32) * nextpow2(dims.width)))

	w = round_up(dims.width, 32)
	h = round_up(dims.height, 32)
	d = min((((w - 1) * (h - 1) // 0x8000) + 2), 0xff)
	cassert(dims.slice_data_size // 0x4000, d)
	cassert(dims.slice_data_size, min((((w - 1) * (h - 1) // 0x8000) + 2), 0xff) * 0x4000)

	w = dims.width
	h = dims.height
	width_mbs = (dims.width + 15) // 16
	height_mbs = (dims.height + 15) // 16
	assert((dims.rvra_size3 & (0x100 - 1) == 0))
	d = (dims.rvra_size3 // 0x100) - 64
	q = dims.rvra_size3
	print(f"{str(w).rjust(4)} {str(h).rjust(4)} {str(d).rjust(4)} {str(hex(q)).rjust(4)}")


def main(paths):
	fp0 = AVDH264V3FrameParams.parse(open(paths[0], "rb").read())
	fp1 = AVDH264V3FrameParams.parse(open(paths[1], "rb").read())
	fp2 = AVDH264V3FrameParams.parse(open(paths[2], "rb").read())
	#print(fp2)

	dims = dotdict()
	dims.width = (fp0.hdr.hdr_3c_height_width & 0xffff) + 1
	dims.height = (fp0.hdr.hdr_3c_height_width >> 16) + 1

	dims.y_addr = fp0.hdr.hdr_210_y_addr_lsb8 << 8
	dims.uv_addr = fp0.hdr.hdr_214_uv_addr_lsb8 << 8

	dims.slice_data_addr = fp0.slc.slc_a84_slice_addr_low_notused & 0xffffff00
	dims.slice_data_size = (fp0.hdr.hdr_bc_sps_tile_addr_lsb8 << 8) - dims.slice_data_addr

	dims.sps_tile_addr = fp0.hdr.hdr_bc_sps_tile_addr_lsb8 << 8
	dims.sps_tile_size = (fp1.hdr.hdr_bc_sps_tile_addr_lsb8 - fp0.hdr.hdr_bc_sps_tile_addr_lsb8) << 8
	dims.pps_tile_addr = fp0.hdr.hdr_9c_pps_tile_addr_lsb8[0] << 8
	dims.pps_tile_size = (fp0.hdr.hdr_9c_pps_tile_addr_lsb8[1] - fp0.hdr.hdr_9c_pps_tile_addr_lsb8[0]) << 8

	dims.rvra0_addr = fp0.hdr.hdr_c0_curr_ref_addr_lsb7[1] << 7
	dims.rvra1_addr = fp1.hdr.hdr_c0_curr_ref_addr_lsb7[1] << 7

	dims.rvra_size0 = (fp1.hdr.hdr_c0_curr_ref_addr_lsb7[0] - fp1.hdr.hdr_c0_curr_ref_addr_lsb7[1]) << 7
	dims.rvra_size1 = (fp1.hdr.hdr_c0_curr_ref_addr_lsb7[3] - fp1.hdr.hdr_c0_curr_ref_addr_lsb7[0]) << 7
	dims.rvra_size2 = (fp1.hdr.hdr_c0_curr_ref_addr_lsb7[2] - fp1.hdr.hdr_c0_curr_ref_addr_lsb7[3]) << 7
	dims.rvra_size3 = ((fp2.hdr.hdr_c0_curr_ref_addr_lsb7[0] - fp1.hdr.hdr_c0_curr_ref_addr_lsb7[0]) << 7) - dims.rvra_size2 - dims.rvra_size1 - dims.rvra_size0
	dims.rvra_total_size = (fp2.hdr.hdr_c0_curr_ref_addr_lsb7[0] - fp1.hdr.hdr_c0_curr_ref_addr_lsb7[0]) << 7
	cassert((fp0.hdr.hdr_c0_curr_ref_addr_lsb7[0] << 7), (dims.rvra0_addr + dims.rvra_size0))
	cassert((fp0.hdr.hdr_c0_curr_ref_addr_lsb7[3] << 7), (dims.rvra0_addr + dims.rvra_size0 + dims.rvra_size1))
	cassert((fp0.hdr.hdr_c0_curr_ref_addr_lsb7[2] << 7), (dims.rvra0_addr + dims.rvra_size0 + dims.rvra_size1 + dims.rvra_size2))
	cassert(dims.rvra_total_size, (dims.rvra_size0 + dims.rvra_size1 + dims.rvra_size2 + dims.rvra_size3))

	rvras = []
	sps_tile_count = 0
	for i,path in enumerate(paths):
		fp = AVDH264V3FrameParams.parse(open(path, "rb").read())
		addr = fp.hdr.hdr_c0_curr_ref_addr_lsb7[1] << 7
		rvras.append(addr)

		addr = fp.hdr.hdr_bc_sps_tile_addr_lsb8 << 8
		if ((i) and (not sps_tile_count) and (addr == dims.sps_tile_addr)):
			sps_tile_count = i
			dims.sps_tile_count = i

	rvras = sorted(list(set(rvras)))
	assert(rvras[0] == 0x734000)
	assert(rvras[1] == (dims.rvra1_addr))
	rvra1_range = rvras[-1] - rvras[1]
	assert(not(rvra1_range % dims.rvra_total_size))
	dims.rvra_count = rvra1_range // dims.rvra_total_size
	assert((dims.rvra_count <= 16))
	test(dims)

def get_dims(dirname):
	paths = os.listdir(dirname)
	paths = sorted([os.path.join(dirname, path) for path in paths if "frame" in path])[:25]
	main(paths)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='Generate instruction stream')
	parser.add_argument('-d','--dir', type=str, default="", help="trace dir name")
	parser.add_argument('-p','--prefix', type=str, default="", help="dir prefix")
	args = parser.parse_args()
	args.dir = resolve_input(args.dir, isdir=True)
	args.prefix = "/home/eileen/asahi/m1n1/proxyclient/data/h264-old"

	all_dirs = []
	for r in ["red-h264", "testsrc-h264", "matrix-h264", "big-h264"]:
		x = [os.path.join(args.prefix, r, t) for t in os.listdir(os.path.join(args.prefix, r))]
		all_dirs += x
	dirs = sorted(all_dirs, key = lambda x: (int(x.rsplit("-", 1)[1].split("x")[0]), int(x.rsplit("-", 1)[1].split("x")[1])))
	for d in dirs:
		get_dims(os.path.join(args.prefix, d))
