#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..decoder import AVDDecoder
from ..utils import *
from .fp import AVDH265V3FrameParams
from .halv3 import AVDH265HalV3
from .parser import AVDH265Parser
from .types import *

class AVDH265Ctx(dotdict):
	pass

class AVDH265Picture(dotdict):
	def __repr__(self):
		x = self.addr >> 7 if self.lsb7 else self.addr >> 8
		return f"[addr: {hex(x).ljust(2+5)} poc: {str(self.poc).ljust(3)} idx: {str(self.idx).ljust(1)} flags: {format(self.flags, '010b')} access_idx: {str(self.access_idx).ljust(3)} rasl: {str(int(self.rasl))}]"

	def unref(self):
		self.flags = 0

class AVDH265Decoder(AVDDecoder):
	def __init__(self):
		super().__init__(AVDH265Parser, AVDH265HalV3, AVDH265V3FrameParams)
		self.mode = "h265"

	def get_pps(self, sl):
		return self.ctx.pps_list[sl.slice_pic_parameter_set_id]

	def get_sps_id(self, sl):
		return self.get_pps(sl).pps_seq_parameter_set_id

	def get_sps(self, sl):
		return self.ctx.sps_list[self.get_sps_id(sl)]

	def allocate_fifo(self):
		ctx = self.ctx
		self.reset_allocator()
		ctx.inst_fifo_count = 7
		ctx.inst_fifo_idx = 0
		ctx.inst_fifo_addrs = [0 for n in range(ctx.inst_fifo_count)]
		self.allocator_move_up(0x18000)
		for n in range(ctx.inst_fifo_count):
			ctx.inst_fifo_addrs[n] = self.range_alloc(0x100000, pad=0x4000, name="inst_fifo%d" % n)
		ctx.inst_fifo_iova = ctx.inst_fifo_addrs[ctx.inst_fifo_idx]

	def new_context(self, vps_list, sps_list, pps_list):
		self.ctx = AVDH265Ctx()
		ctx = self.ctx
		ctx.vps_list = vps_list
		ctx.sps_list = sps_list
		ctx.pps_list = pps_list

		ctx.access_idx = 0
		ctx.width = -1
		ctx.height = -1
		ctx.active_sl = None
		ctx.cur_sps_id = -1

		ctx.last_intra = 0
		ctx.last_p_sps_tile_idx = 0
		ctx.dpb_list = []
		ctx.ref_lst = [[None for n in range(64)] for n in range(5)]
		ctx.ref_lst_cnt = [0, 0, 0, 0, 0]
		ctx.poc = -1
		self.allocate_fifo()

	def refresh_sps(self, sl):
		ctx = self.ctx
		sps_id = self.get_sps_id(sl)
		if (sps_id == ctx.cur_sps_id):
			return
		sps = ctx.sps_list[sps_id]
		width = sps.pic_width_in_luma_samples
		height = sps.pic_height_in_luma_samples

		ctx.orig_width = width
		ctx.orig_height = height
		if (width & 1):
			width = round_up(width, 2)
		if (height & 1):
			height = round_up(height, 2)
		if ((width != ctx.orig_width) or (height != ctx.orig_height)):
			self.log("dimensions changed from %dx%d -> %dx%d" % (ctx.width, ctx.height, width, height))
		ctx.width = width
		ctx.height = height

		assert((64 <= width and width <= 4096) and (64 <= height and height <= 4096)) # hardware caps
		assert(not(width & 1) and not(height & 1)) # hardware caps
		ctx.cur_sps_id = sps_id
		self.allocate_buffers()

	def allocate_buffers(self):
		ctx = self.ctx
		sps = ctx.sps_list[ctx.cur_sps_id]

		rvra_total_size = self.calc_rvra(is_422=sps.chroma_format_idc == HEVC_CHROMA_IDC_422)
		self.allocator_move_up(0x734000)
		ctx.rvra_count = 6
		ctx.rvra_base_addrs = [0 for n in range(ctx.rvra_count)]
		ctx.rvra_base_addrs[0] = self.range_alloc(rvra_total_size, pad=0x100, name="rvra0")

		if (not(isdiv(ctx.width, 32))):
			wr = round_up(ctx.width, 64)
		else:
			wr = round_up(ctx.width, 16)
		ctx.luma_size = wr * ctx.height
		ctx.y_addr = self.range_alloc(ctx.luma_size, name="disp_y")
		ctx.chroma_size = wr * round_up(ctx.height, 16)
		if (sps.chroma_format_idc == HEVC_CHROMA_IDC_420):
			ctx.chroma_size //= 2
		ctx.uv_addr = self.range_alloc(ctx.chroma_size, name="disp_uv")

		ctx.slice_data_size = min((((round_up(ctx.width, 32) - 1) * (round_up(ctx.height, 32) - 1) // 0x8000) + 2), 0xff) * 0x4000
		ctx.slice_data_addr = self.range_alloc(ctx.slice_data_size, align=0x4000, padb4=0x4000, name="slice_data")

		ctx.sps_tile_count = 16
		ctx.sps_tile_addrs = [0 for n in range(ctx.sps_tile_count)]
		n = max(rounddiv(ctx.height * ctx.width, 0x40000), 1) + 1
		sps_tile_size = n * 0x4000
		for n in range(ctx.sps_tile_count):
			ctx.sps_tile_addrs[n] = self.range_alloc(sps_tile_size, name="sps_tile%d" % n)

		pps_tile_count = 5
		ctx.pps_tile_addrs = [0 for n in range(pps_tile_count)]
		for n in range(pps_tile_count):
			ctx.pps_tile_addrs[n] = self.range_alloc(0x8000, name="pps_tile%d" % n)

		for n in range(ctx.rvra_count - 1):
			ctx.rvra_base_addrs[n + 1] = self.range_alloc(rvra_total_size, name="rvra1_%d" % n)
		self.dump_ranges()

		ctx.dpb_pool = []
		for i in range(ctx.rvra_count):
			pic = AVDH265Picture(addr=ctx.rvra_base_addrs[i], idx=i, poc=-1, flags=0, type=-1, lsb7=True, rasl=0, access_idx=-1)
			ctx.dpb_pool.append(pic)
			self.log(f"DPB Pool: {pic}")

	def refresh(self, sl):
		self.refresh_sps(sl)
		self.realloc_rbsp_size(sl)

	def setup(self, path, num=0, **kwargs):
		vps_list, sps_list, pps_list, slices = self.parser.parse(path, num=num)
		self.new_context(vps_list, sps_list, pps_list)
		# realistically we'd have the height/width as metadata w/o relying on sps
		self.refresh(slices[0])
		return slices

	def construct_ref_list(self):
		ctx = self.ctx; sl = self.ctx.active_sl
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
		sl.reflist = reflist
		ctx.dpb_list = dpb_list

	def bump_frame(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		dpb = 0
		for frame in ctx.dpb_list:
			if (frame.flags and frame.poc != sl.poc):
				dpb += 1
		print(self.get_sps(sl))
		raise ValueError("uh")

	def find_ref_idx(self, poc):
		ctx = self.ctx; sl = self.ctx.active_sl
		cands = [pic for pic in ctx.dpb_pool if pic.poc == poc]
		assert(len(cands) <= 1)
		if (len(cands) == 0):
			return None
		return cands[0]

	def get_free_pic(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		cands = [pic for pic in ctx.dpb_pool if not (pic.flags & HEVC_FRAME_FLAG_SHORT_REF)]
		cand = cands[0] # this refill algo isn't same as macOS but it doesnt matter
		cand.flags |= (HEVC_FRAME_FLAG_SHORT_REF)
		return cand

	def generate_missing_ref(self, poc, t):
		ctx = self.ctx; sl = self.ctx.active_sl
		pic = self.get_free_pic()
		pic.flags = 0
		raise ValueError("uh")

	def add_candidate_ref(self, t, poc, flags):
		ctx = self.ctx; sl = self.ctx.active_sl
		# add a reference with the given poc to the list and mark it as used in DPB
		ref = self.find_ref_idx(poc)
		if (ref == None):
			ref = self.generate_missing_ref(poc, t)
		lst = ctx.ref_lst[t]
		lst[ctx.ref_lst_cnt[t]] = ref
		ref.flags |= flags
		ctx.ref_lst_cnt[t] += 1

	def do_frame_rps(self):
		ctx = self.ctx; sl = self.ctx.active_sl

		for x in ctx.dpb_pool:
			self.log(f"DPB Pool: {x}")

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

	def set_new_ref(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		ref = self.get_free_pic()
		ref.type = HEVC_REF_ST
		ref.poc = ctx.poc
		if (sl.pic_output_flag):
		    ref.flags |= HEVC_FRAME_FLAG_OUTPUT | HEVC_FRAME_FLAG_SHORT_REF
		else:
		    ref.flags |= HEVC_FRAME_FLAG_SHORT_REF
		ref.rasl = IS_IDR(sl) or IS_BLA(sl) or (sl.nal_unit_type == HEVC_NAL_CRA_NUT)
		ref.access_idx = ctx.access_idx
		sl.pic = ref
		self.log(f"INDEX: {ref.idx}")

	def init_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		ctx.poc = sl.pic_order_cnt

		self.refresh(sl)

		if (sl.first_slice_segment_in_pic_flag):
			self.set_new_ref()
			self.log(f"curr: {sl.pic}")
			self.do_frame_rps()

		if ((not sl.dependent_slice_segment_flag) and (sl.slice_type != HEVC_SLICE_I)):
			self.construct_ref_list()

	def finish_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl

		ctx.last_intra = IS_INTRA(sl)
		ctx.access_idx += 1
