#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
# H.265 Reference List Management Logic

from ..utils import dotdict
from .types import *

class AVDH265Picture(dotdict):
	def __repr__(self):
		x = self.addr >> 7 if self.lsb7 else self.addr >> 8
		return f"[addr: {hex(x).ljust(2+5)} poc: {str(self.poc).ljust(3)} idx: {str(self.idx).ljust(1)} flags: {format(self.flags, '010b')} access_idx: {str(self.access_idx).ljust(3)} rasl: {str(int(self.rasl))}]"

	def unref(self):
		self.flags = 0

class AVDH265RLM:
	def __init__(self, dec):
		self.dec = dec
		self.ctx = None

	def log(self, x):
		self.dec.log(x, cl="RLM")

	def construct_ref_list(self, sl):
		ctx = self.ctx
		if (sl.slice_type == HEVC_SLICE_P):
			lx_count = 1
		else:
			lx_count = 2
		dpb_list = []
		reflist = [None, None]
		for lx in range(lx_count):
			num_ref_idx_lx_active = sl[f"num_ref_idx_l{lx}_active_minus1"] + 1
			nb_refs = 0
			rpl_tmp = [None for n in range(HEVC_MAX_REFS)]
			cand_lists = [ST_CURR_AFT if lx else ST_CURR_BEF,
						  ST_CURR_BEF if lx else ST_CURR_AFT,
						  LT_CURR]
			while (nb_refs < num_ref_idx_lx_active):
				for i in range(len(cand_lists)):
					lst = ctx.ref_lst[cand_lists[i]]
					for j in range(min(ctx.ref_lst_cnt[cand_lists[i]], HEVC_MAX_REFS)):
						if (nb_refs >= num_ref_idx_lx_active): break
						rpl_tmp[nb_refs] = lst[j]
						nb_refs += 1
			reflist[lx] = rpl_tmp[:nb_refs]
			for x in reflist[lx]:
				self.log(f"List{lx}: {x}")
				if (x not in dpb_list):
					dpb_list.append(x)
		ctx.dpb_list = dpb_list
		return reflist

	def bump_frame(self):
		ctx = self.ctx
		dpb = 0
		for frame in ctx.dpb_list:
			if (frame.flags and frame.poc != sl.poc):
				dpb += 1
		raise ValueError("TODO")

	def find_ref_idx(self, poc):
		ctx = self.ctx
		cands = [pic for pic in ctx.dpb_pool if pic.poc == poc]
		assert(len(cands) <= 1)
		if (len(cands) == 0):
			return None
		return cands[0]

	def get_free_pic(self):
		ctx = self.ctx
		cands = [pic for pic in ctx.dpb_pool if not (pic.flags & HEVC_FRAME_FLAG_SHORT_REF)]
		cand = cands[0] # this refill algo isn't same as macOS but it doesnt matter
		cand.flags |= (HEVC_FRAME_FLAG_SHORT_REF)
		return cand

	def generate_missing_ref(self, poc, t):
		ctx = self.ctx
		pic = self.get_free_pic()
		pic.flags = 0
		raise ValueError("TODO")

	def add_candidate_ref(self, t, poc, flags):
		ctx = self.ctx
		# add a reference with the given poc to the list and mark it as used in DPB
		ref = self.find_ref_idx(poc)
		if (ref == None):
			ref = self.generate_missing_ref(poc, t)
		lst = ctx.ref_lst[t]
		lst[ctx.ref_lst_cnt[t]] = ref
		ref.flags |= flags
		ctx.ref_lst_cnt[t] += 1

	def do_frame_rps(self, sl):
		ctx = self.ctx

		if (not IS_IDR(sl)):
			for x in ctx.dpb_pool:
				if (x.idx == sl.pic.idx): continue
				x.flags &= ~(HEVC_FRAME_FLAG_SHORT_REF)

			for t in range(NB_RPS_TYPE):
				ctx.ref_lst_cnt[t] = 0

			for i in range(sl.st_rps_num_delta_pocs):
				poc = sl.st_rps_poc[i]
				if (not sl.st_rps_used[i]):
					t = ST_FOLL
				elif (i < sl.st_rps_num_negative_pics):
					t = ST_CURR_BEF
				else:
					t = ST_CURR_AFT
				self.add_candidate_ref(t, poc, HEVC_FRAME_FLAG_SHORT_REF)

		if (sl.nal_unit_type == HEVC_NAL_CRA_NUT):
			for i in range(ctx.ref_lst_cnt[ST_FOLL]):
				ref = ctx.ref_lst[ST_FOLL][i]
				ref.poc = sl.st_rps_poc[i]
				ref.flags &= ~(HEVC_FRAME_FLAG_OUTPUT)

		if (not IS_IRAP(sl)):
			self.bump_frame()

	def set_new_ref(self, sl, poc):
		ctx = self.ctx
		ref = self.get_free_pic()
		ref.type = HEVC_REF_ST
		ref.poc = poc
		if (sl.pic_output_flag):
			ref.flags |= HEVC_FRAME_FLAG_OUTPUT | HEVC_FRAME_FLAG_SHORT_REF
		else:
			ref.flags |= HEVC_FRAME_FLAG_SHORT_REF
		ref.rasl = IS_IDR(sl) or IS_BLA(sl) or (sl.nal_unit_type == HEVC_NAL_CRA_NUT)
		ref.access_idx = ctx.access_idx
		self.log(f"Index: {ref.idx}")
		return ref
