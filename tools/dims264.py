#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import os

from avid.h264.fp import *
from avid.utils import *
from tools.common import cassert

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
	if (scale >= 32) or (min(dims.height, dims.width) <= 128):
		luma_size = dims.height * dims.width
	else:
		luma_size = round_up(dims.width, 64) * round_up(dims.height, 64)
	x = dims.y_addr + luma_size
	cassert(dims.uv_addr, x)

	scale = min(pow2div(dims.height), pow2div(dims.width))
	if (scale >= 32) or (min(dims.height, dims.width) <= 128):
		chroma_size = dims.height * dims.width // 2
	else:
		chroma_size = round_up(dims.height * dims.width // 2, 0x4000)
	x = round_up(dims.uv_addr + chroma_size, 0x4000) + 0x4000 # this one they just pad lazily
	if (dims.height in [336, 4096]):
		x += 0x4000
	cassert(dims.slice_data_addr, x)

	cassert(dims.sps_tile_count, 24)
	cassert(dims.pps_tile_size, 0x8000)

	cassert(dims.sps_tile_addr, (dims.slice_data_addr + dims.slice_data_size))
	cassert(dims.pps_tile_addr, (dims.sps_tile_addr + (dims.sps_tile_size * dims.sps_tile_count)))
	cassert(dims.rvra1_addr, (dims.pps_tile_addr + (dims.pps_tile_size * 5))) # const

	width_mbs = (dims.width + 15) // 16
	height_mbs = (dims.height + 15) // 16
	#x = (396 // (height_mbs * width_mbs)) # DPB
	#print(dims.rvra_count, x, hex((1024 * 396) // (dims.rvra_count + 1)), hex(dims.rvra_size3))

	ws = round_up(dims.width, 32)
	hs = round_up(dims.height, 32)
	# 00734000: 51515151 51515151 51515151 51515151 51515151 51515151 51515151 51515151 0
	# 00734400: 51515151 51515151 51515151 51515151 51515151 51515151 51515151 51515151 1
	# ...
	# 00735c00: 51515151 51515151 51515151 51515151 51515151 51515151 51515151 51515151 8
	cassert(dims.rvra_size0, (hs * ws) + ((hs * ws) // 4)) # luma

	# 00736900: f05af05a f05af05a f05af05a f05af05a 00000000 00000000 00000000 00000000 0
	# 00736b00: f05af05a f05af05a f05af05a f05af05a 00000000 00000000 00000000 00000000 1
	# ...
	# 00737700: f05af05a f05af05a f05af05a f05af05a 00000000 00000000 00000000 00000000 8
	cassert(dims.rvra_size2, (dims.rvra_size0 // 2))  # 4:2:0 chroma

	cassert(dims.rvra_size1, ((nextpow2(dims.height) // 32) * nextpow2(dims.width)))

	"""
	64x64
	00735e80 01010101 0b460506 05060101 4c4d484a 120d4e0b 0101494a 53111250 01014b4b

	64x80
	00736e00 01010101 01050101 01010101 474b4b48 510d4e4b 5453c956 544e4f4d 5454c8c6
	00736e20 010101c6 00000000 01010101 00000000 00000000 00000000 00000000 00000000

	64x96
	00736e00 01010101 01010101 01010101 464a0606 0e460606 4dc75307 4e4b014a c7c64dca
	00736e20 154b110c 01010701 4b4e0c0f 01010101 00000000 00000000 00000000 00000000
	"""
	# at least (16 * clog2(dims.height) * clog2(dims.height))
	x = clog2(dims.width) - 6
	y = clog2(dims.height) - 6
	s = dims.width * dims.height
	m = x * y
	#print(dims.width, dims.height, hex(dims.rvra_size3), hex(m))
	#print(dims.height, y, 2 ** (y + 5), dims.width, x)
	#assert(dims.rvra_size3 >= (64 * x * y))

def main(paths):
	fp0 = AvdH264V3FrameParams.parse(open(paths[0], "rb").read())
	fp1 = AvdH264V3FrameParams.parse(open(paths[1], "rb").read())
	fp2 = AvdH264V3FrameParams.parse(open(paths[2], "rb").read())
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
		fp = AvdH264V3FrameParams.parse(open(path, "rb").read())
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
	paths = sorted([os.path.join(dirname, path) for path in paths if "param" in path or "frame" in path])[:25]
	main(paths)

if __name__ == "__main__":
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument('-d','--dir', type=str, help="trace dir name")
	parser.add_argument('-p','--prefix', type=str, default="", help="dir prefix")
	args = parser.parse_args()
	get_dims(os.path.join(args.prefix, args.dir))
