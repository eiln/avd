#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
from tools.common import ffprobe, resolve_input

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='Generate instruction stream')
	parser.add_argument('input', type=str, help="path to bitstream")
	parser.add_argument('-n', '--num', type=int, default=1, help="count")
	parser.add_argument('-a', '--all', action='store_true', help="run all")
	parser.add_argument('-sh', '--show-headers', action='store_true', help="run all")
	parser.add_argument('-q', '--do-probs', action='store_true', help="run all")
	args = parser.parse_args()

	path = resolve_input(args.input)
	mode = ffprobe(path)
	if  (mode == "h264"):
		from avid.h264.decoder import AVDH264Decoder
		dec = AVDH264Decoder()
	elif (mode == "vp09"):
		from avid.vp9.decoder import AVDVP9Decoder
		dec = AVDVP9Decoder()
	elif  (mode == "h265"):
		from avid.h265.decoder import AVDH265Decoder
		dec = AVDH265Decoder()
	else:
		raise ValueError("Not supported")

	num = 0 if args.all else args.num
	units = dec.setup(path, num=num, nal_stop=1, do_probs=args.do_probs)

	if (args.show_headers):
		if  (mode == "h264" or mode == "h265"):
			if (mode == "h265"):
				for n in range(len(dec.ctx.vps_list)):
					if (dec.ctx.vps_list[n]):
						print(dec.ctx.vps_list[n])
			for n in range(len(dec.ctx.sps_list)):
				if (dec.ctx.sps_list[n]):
					print(dec.ctx.sps_list[n])
			for n in range(len(dec.ctx.pps_list)):
				if (dec.ctx.pps_list[n]):
					print(dec.ctx.pps_list[n])

	for unit in units[:num]:
		if (args.show_headers):
			print(unit)
		inst = dec.decode(unit)
		print()
