#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import os
from construct import *
import numpy as np
from avid.constructutils import *

class ProbsConstructClass(ConstructClass):
	def __init__(self):
		super().__init__()

	def _post_parse(self, obj):
		for key in list(obj):
			if (key.startswith("_") or "pad" in key): continue
			obj[key] = np.array(obj[key])
		return obj

class AVDVP9MvProbs(ProbsConstructClass):
	subcon = Struct(
		"sign" / Int8ul,
		"classes" / Array(10, Int8ul),
		"class0" / Int8ul,
		"bits" / Array(10, Int8ul),
	)
	_spacecnt = 1
	def __init__(self):
		super().__init__()

class AVDVP9MvFpProbs(ProbsConstructClass):
	subcon = Struct(
		"class0_fp" / Array(2, (Array(3, Int8ul))),
		"fp" / Array(3, Int8ul),
	)
	_spacecnt = 1
	def __init__(self):
		super().__init__()

class AVDVP9MvHpProbs(ProbsConstructClass):
	subcon = Struct(
		"class0_hp" / Int8ul,
		"hp" / Int8ul,
	)
	_spacecnt = 1
	def __init__(self):
		super().__init__()

class AVDVP9Probs(ProbsConstructClass):
	subcon = Struct(
		"padding" / ExprValidator(Array(10, Int8ul), obj_ == [0] * 10),
		"tx8p" / Array(2, (Array(1, Int8ul))),
		"tx16p" / Array(2, (Array(2, Int8ul))),
		"tx32p" / Array(2, (Array(3, Int8ul))),
		"coef" / Array(1584, Int8ul),
		"skip" / Array(3, Int8ul),
		"inter_mode" / Array(7, (Array(3, Int8ul))),
		"switchable_interp" / Array(4, (Array(2, Int8ul))),
		"intra_inter" / Array(4, Int8ul),
		"comp_inter" / Array(5, Int8ul),
		"single_ref" / Array(5, (Array(2, Int8ul))),
		"comp_ref" / Array(5, Int8ul),
		"y_mode" / Array(4, (Array(9, Int8ul))),
		"uv_mode" / Array(10, (Array(9, Int8ul))),
		"partition" / Array(4, (Array(4, Array(3, Int8ul)))),
		"mv_joint" / Array(3, Int8ul),
		"mv_comp" / Array(2, AVDVP9MvProbs), # v, h
		"mv_fp" / Array(2, AVDVP9MvFpProbs), # v, h
		"mv_hp" / Array(2, AVDVP9MvHpProbs), # v, h
	)
	assert(subcon.sizeof() == 1905)

	def __init__(self):
		super().__init__()

	def _post_parse(self, obj):
		count = 0
		for key in list(obj):
			if (key.startswith("_") or "pad" in key or key == "coef"): continue
			if (key in ["mv_fp", "mv_hp", "mv_comp"]): continue
			obj[key] = np.array(obj[key])

		coef = np.zeros((4, 2, 2, 6, 6, 3), dtype=np.uint8)
		for i in range(4):
			for j in range(2):
				for k in range(2):
					for l in range(6):
						for m in range(6):
							if (m >= 3 and l == 0): # dc only has 3 pt
				                                break
							for n in range(3):
								coef[i][j][k][l][m][n] = obj["coef"][count]
								count += 1
		obj["coef"] = coef
		return obj

class FFVP9MvProbs(ProbsConstructClass):
	subcon = Struct(
		"sign" / Int8ul,
		"classes" / Array(10, Int8ul),
		"class0" / Int8ul,
		"bits" / Array(10, Int8ul),
		"class0_fp" / Array(2, (Array(3, Int8ul))),
		"fp" / Array(3, Int8ul),
		"class0_hp" / Int8ul,
		"hp" / Int8ul,
	)
	_spacecnt = 1
	def __init__(self):
		super().__init__()

class FFVP9Probs(ProbsConstructClass):
	subcon = Struct(
		"y_mode" / Array(4, (Array(9, Int8ul))),
		"uv_mode" / Array(10, (Array(9, Int8ul))),
		"partition" / Array(16, Array(3, Int8ul)),
		"switchable_interp" / Array(4, (Array(2, Int8ul))),
		"inter_mode" / Array(7, (Array(3, Int8ul))),
		"intra_inter" / Array(4, Int8ul),
		"comp_inter" / Array(5, Int8ul),
		"single_ref" / Array(5, (Array(2, Int8ul))),
		"comp_ref" / Array(5, Int8ul),
		"tx32p" / Array(2, (Array(3, Int8ul))),
		"tx16p" / Array(2, (Array(2, Int8ul))),
		"tx8p" / Array(2, (Array(1, Int8ul))),
		"skip" / Array(3, Int8ul),
		"mv_joint" / Array(3, Int8ul),
		"mv_comp" / Array(2, FFVP9MvProbs), # v, h
		"coef" / Array(4, (Array(2, Array(2, Array(6, Array(6, Array(3, Int8ul))))))),
	)
	def __init__(self):
		super().__init__()

	def _post_parse(self, obj):
		for key in list(obj):
			if (key.startswith("_") or "pad" in key): continue
			obj[key] = np.array(obj[key])

		part = obj["partition"]
		part = part.reshape((4, 4, 3))
		obj["partition"] = part

		#obj["coef"] = obj["coef"].reshape((4, 2, 2, 6, 6, 3))
		return obj

def pprint_probs(probs):
	s = ""
	for key in ["tx8p", "tx16p", "tx32p", "skip", "inter_mode", "switchable_interp", "intra_inter", "comp_inter", "single_ref", "comp_ref", "y_mode", "uv_mode", "partition", "mv_joint", "coef"]:
		s += f"\033[0;36m{key}:\033[0m\n"
		s += str(getattr(probs, key)) + "\n\n"
	return s

def main(paths):
	last = None
	for i in range(10):
		pidx = i * 4 + (i % 4)
		print(paths[pidx])
		probs = open(paths[pidx], "rb").read()
		avprobs = AVDVP9Probs.parse(probs)
		#print(pprint_probs(avprobs))

		probs = open("/home/eileen/asahi/avd/codecs/out/p%d.bin" % i, "rb").read()
		ffprobs = FFVP9Probs.parse(probs)
		#print(pprint_probs(ffprobs))

		for key in ["tx8p", "tx16p", "tx32p", "skip", "inter_mode", "switchable_interp", "intra_inter", "comp_inter", "single_ref", "comp_ref", "y_mode", "uv_mode", "partition", "mv_joint", "coef"]:
			if key != "skip": continue
			a = avprobs[key]
			b = ffprobs[key]
			if (last):
				c = last[key]
				if 0:
					if (not np.array_equal(a, c)):
						print(key)
						print(a)
						print(a - c)
					#print(np.array_equal(a, c))
			if 1:
				if (not np.array_equal(a, b)):
					print(key)
					print(a)
					print(b)
					#print(a - b)
		last = avprobs
		print("="*100)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='macOS frame_params parser')
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument('-i', '--input', type=str, help="path to frame_params")
	group.add_argument('-d','--dir', type=str, help="frame_params dir name")
	parser.add_argument('-p','--prefix', type=str, default="", help="dir prefix")
	parser.add_argument('-s', '--start', type=int, default=0, help="starting index")
	parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
	parser.add_argument('-a', '--all', action='store_true', help="run all")
	args = parser.parse_args()

	if args.dir:
		paths = os.listdir(os.path.join(args.prefix, args.dir))
		paths = sorted([os.path.join(args.prefix, args.dir, path) for path in paths if "prob" in path])
		paths = paths if args.all else paths[args.start:args.start+args.num]
	else:
		paths = [args.input]

	main(paths)
