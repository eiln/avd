#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import os
from construct import *
import numpy as np

from avid.vp9.decoder import AVDVP9Decoder
from avid.vp9.probs import *
from tools.common import bassert

def testdiff(key, a, b):
	if (not np.array_equal(a, b)):
		print(key)
		print(a)
		print(b)
		print(a - b)

def main(slices, paths, count):
	for i in range(count):
		pidx = i * 4 + (i % 4)
		if (pidx > len(paths)):
			break
		print("%03d: %s" % (i, paths[pidx]))
		probs = open(paths[pidx], "rb").read()[:AVDVP9Probs.sizeof()]
		avprobs = AVDVP9Probs.parse(probs)
		myprobs = slices[i].probs
		for key in ["tx8p", "tx16p", "tx32p", "coef", "skip", "inter_mode", "switchable_interp", "intra_inter", "comp_inter", "single_ref", "comp_ref", "y_mode", "uv_mode", "partition", "mv_joint"]:
			a = avprobs[key]
			b = myprobs[key]
			testdiff(key, a, b)
		for j in range(2):
			for key in ["sign", "classes", "class0", "bits", "class0_fp", "fp", "class0_hp", "hp"]:
				a = avprobs["mv_comp"][j][key]
				b = myprobs["mv_comp"][j][key]
				testdiff(key, a, b)
		c = myprobs.to_avdprobs(myprobs)
		bassert(probs, c)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='macOS frame_params parser')
	parser.add_argument('-i', '--input', type=str, help="path to bitstream")
	parser.add_argument('-d','--dir', type=str, help="frame_params dir name")
	parser.add_argument('-p','--prefix', type=str, default="", help="dir prefix")
	parser.add_argument('-n','--count', type=int, default=1, help="count")
	parser.add_argument('-a', '--all', action='store_true', help="run all")
	args = parser.parse_args()

	paths = os.listdir(os.path.join(args.prefix, args.dir))
	paths = sorted([os.path.join(args.prefix, args.dir, path) for path in paths if "prob" in path])
	assert(len(paths))

	count = len(paths) if args.all else args.count
	dec = AVDVP9Decoder()
	slices = dec.parse(args.input)
	main(slices, paths, count)
