#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..probs import *
from itertools import chain

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
		"align" / ZPadding(3), # let's pad it to 4
	)
	assert(subcon.sizeof() == 1905 + 3)

	def __init__(self):
		super().__init__()

	def _post_parse(self, obj):
		count = 0
		for key in list(obj):
			if (key.startswith("_") or key in ["padding", "coef"]): continue
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

		mv_comps = []
		for i in range(2):
			mv_comp = {}
			for key in ["sign", "classes", "class0", "bits"]:
				mv_comp[key] = obj["mv_comp"][i][key]
			for key in ["class0_fp", "fp"]:
				mv_comp[key] = obj["mv_fp"][i][key]
			for key in ["class0_hp", "hp"]:
				mv_comp[key] = obj["mv_hp"][i][key]
			mv_comps.append(mv_comp)
		obj["mv_comp"] = mv_comps
		return obj

class LibVP9MvProbs(ProbsConstructClass):
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

class LibVP9Probs(ProbsConstructClass):
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
		"mv_comp" / Array(2, LibVP9MvProbs), # v, h
		"coef" / Array(4, (Array(2, Array(2, Array(6, Array(6, Array(3, Int8ul))))))),
	)
	def __init__(self):
		super().__init__()

	def _post_parse(self, obj):
		for key in list(obj):
			if (key.startswith("_") or key in ["mv_comp"]): continue
			obj[key] = np.array(obj[key])
		part = obj["partition"]
		part = part.reshape((4, 4, 3))
		obj["partition"] = part
		return obj

	def to_avdprobs(self, obj):
		# yes this sucks but so does this data structure
		# and python construct doesn't support nested lists for init
		s = Struct(
			"padding" / Default(Array(10, Int8ul), [0]*10),
			"tx8p" / Array(2, Int8ul),
			"tx16p" / Array(2 * 2, Int8ul),
			"tx32p" / Array(2 * 3, Int8ul),
			"coef" / Array(1584, Int8ul),
			"skip" / Array(3, Int8ul),
			"inter_mode" / Array(7 * 3, Int8ul),
			"switchable_interp" / Array(4 * 2, Int8ul),
			"intra_inter" / Array(4, Int8ul),
			"comp_inter" / Array(5, Int8ul),
			"single_ref" / Array(5 * 2, Int8ul),
			"comp_ref" / Array(5, Int8ul),
			"y_mode" / Array(4 * 9, Int8ul),
			"uv_mode" / Array(10 * 9, Int8ul),
			"partition" / Array(4 * 4 * 3, Int8ul),
			"mv_joint" / Array(3, Int8ul),
			"mv_comp" / Array(2 * (1 + 10 + 1 + 10), Int8ul),
			"mv_fp" / Array(2 * ((2 * 3) + 3), Int8ul),
			"mv_hp" / Array(2 * (1 + 1), Int8ul),
			"align" / ZPadding(3), # let's pad it to 4
		)
		d = {}
		count = 0
		coef = [0] * 1584
		for i in range(4):
			for j in range(2):
				for k in range(2):
					for l in range(6):
						for m in range(6):
							if (m >= 3 and l == 0): # dc only has 3 pt
				                                break
							for n in range(3):
								coef[count] = obj.coef[i][j][k][l][m][n]
								count += 1
		d["coef"] = coef

		mv_comps = []
		mv_fps = []
		mv_hps = []
		for i in range(2):
			mv_comps.append([obj.mv_comp[i][key].flatten().tolist() for key in ["sign", "classes", "class0", "bits"]])
			mv_fps.append([obj.mv_comp[i][key].flatten().tolist() for key in ["class0_fp", "fp"]])
			mv_hps.append([obj.mv_comp[i][key].flatten().tolist() for key in ["class0_hp", "hp"]])
		d["mv_comp"] = mv_comps
		d["mv_fp"] = mv_fps
		d["mv_hp"] = mv_hps

		for key in list(obj):
			if (key.startswith("_")): continue
			if key in d: continue
			v = obj[key]
			d[key] = v
		for key,v in d.items():
			if (isinstance(v, (np.ndarray, np.generic))):
				v = v.flatten().tolist()
			if (any(isinstance(i, list) for i in v)):
				v = list(chain(*v))
				v = list(chain(*v))
			d[key] = v
		p = s.build(d)
		return p
