#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
# H.264 Reference List Management Logic

from .types import *
from dataclasses import dataclass

@dataclass(slots=True)
class AVDH264Picture:
	idx: int
	addr: int
	pic_num: int
	poc: int
	frame_num_wrap: int
	flags: int
	access_idx: int
	sps_idx: int = 0xffffffff
	sps_pic: None = None

	def __repr__(self):
		return f"[idx: {str(self.idx).rjust(2)} addr: {hex(self.addr >> 7).ljust(2+5)} pic_num: {str(self.pic_num).rjust(2)} poc: {str(self.poc).rjust(3)} fn: {str(self.frame_num_wrap).rjust(2)} flags: {format(self.flags, '010b')}]"

class AVDH264RLM:
	def __init__(self, dec):
		self.dec = dec
		self.ctx = None

	def log(self, x):
		self.dec.log(x, cl="RLM")

	def get_short_ref_by_num(self, lst, pic_num):
		cands = [pic for pic in lst if pic and pic.pic_num == pic_num]
		assert(len(cands) == 1)
		return cands[0]

	def modify_ref_list(self, lx, short_refs):
		ctx = self.ctx; sl = self.ctx.active_sl
		lst = getattr(sl, f"list{lx}")
		modification_of_pic_nums_idc = sl[f"modification_of_pic_nums_idc_l{lx}"]
		abs_diff_pic_num_minus1 = sl[f"abs_diff_pic_num_minus1_l{lx}"]
		num_ref_idx_lx_active_minus1 = sl[f"num_ref_idx_l{lx}_active_minus1"]

		pred = sl.pic.pic_num
		for index,mod in enumerate(modification_of_pic_nums_idc):
			if (mod == 3): break
			abs_diff_pic_num = abs_diff_pic_num_minus1[index] + 1
			if (mod == 0 or mod == 1):
				assert(abs_diff_pic_num <= ctx.max_pic_num)
				if (mod == 0):
					pred -= abs_diff_pic_num
				else:
					pred += abs_diff_pic_num
				pred &= ctx.max_pic_num - 1

				sref = self.get_short_ref_by_num(short_refs, pred)
				assert(num_ref_idx_lx_active_minus1 + 1 < 32)

				lst = lst + [None] * ((num_ref_idx_lx_active_minus1 + 1 + 1) - len(lst))
				for i in range(num_ref_idx_lx_active_minus1 + 1, index, -1):
					lst[i] = lst[i - 1]
				lst[index] = sref
				nidx = index
				for i in range(index, num_ref_idx_lx_active_minus1 + 1 + 1):
					if (lst[i] != pred):
						lst[nidx] = lst[i]
						nidx += 1
			elif (mod == 2):
				raise NotImplementedError("LT reordering not yet supported. pls send sample")

		setattr(sl, f"list{lx}", lst)

	def construct_ref_list_p(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		short_refs = [pic for pic in ctx.dpb_list if pic.flags & H264_FRAME_FLAG_SHORT_REF]
		short_refs = sorted(short_refs, key=lambda pic: pic.frame_num_wrap, reverse=True)
		for ref in short_refs:
			self.log(f"P: ST Refs: {ref}")
		long_refs = [pic for pic in ctx.dpb_list if pic.flags & H264_FRAME_FLAG_LONG_REF]
		long_refs = sorted(long_refs, key=lambda pic: pic.pic_num)
		for ref in long_refs:
			self.log(f"P: LT Refs: {ref}")
		sl.list0 = short_refs + long_refs
		if (sl.ref_pic_list_modification_flag_l0):
			self.modify_ref_list(0, short_refs + long_refs)

	def construct_ref_list_b(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		short_refs = [pic for pic in ctx.dpb_list if pic.flags & H264_FRAME_FLAG_SHORT_REF]
		short_refs = sorted(short_refs, key=lambda pic: pic.poc, reverse=True)
		for ref in short_refs:
			self.log(f"B: ST Refs: {ref}")
		sl.list0 = sorted([pic for pic in short_refs if pic.poc < sl.pic.poc], key=lambda pic: pic.poc, reverse=True)
		sl.list1 = sorted([pic for pic in short_refs if pic.poc > sl.pic.poc], key=lambda pic: pic.poc)
		if (sl.ref_pic_list_modification_flag_l0):
			self.modify_ref_list(0, short_refs)
		if (sl.ref_pic_list_modification_flag_l1):
			self.modify_ref_list(1, short_refs)

	def resize_ref_list(self, lx):  # 8.4.2.2
		ctx = self.ctx; sl = self.ctx.active_sl
		lst = getattr(sl, f"list{lx}")
		num = sl[f"num_ref_idx_l{lx}_active_minus1"] + 1

		if (len(lst) > num):
			lst = lst[:num]

		if (len(lst) < num):
			if (lx == 0):  # we use pic_num to index pos in DPB for opcode 2dc
				pic_num = max(x.pic_num for x in lst) + 1
			else:
				pic_num = max(x.pic_num for x in lst) - 1
			for n in range(num - len(lst)):
				pic = AVDH264Picture(addr=0xdead, idx=-1, pic_num=pic_num, poc=-1, frame_num_wrap=-1, flags=0, access_idx=-1)
				self.log(f"Adding missing ref: {pic}")
				lst.append(pic)

		setattr(sl, f"list{lx}", lst)

	def construct_ref_list(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		if (sl.slice_type == H264_SLICE_TYPE_P):
			self.construct_ref_list_p()
		if (sl.slice_type == H264_SLICE_TYPE_B):
			self.construct_ref_list_b()

		if (sl.slice_type == H264_SLICE_TYPE_P) or (sl.slice_type == H264_SLICE_TYPE_B):
			self.resize_ref_list(0)
			for x in sl.list0:
				self.log(f"list0: {x}")
			if (sl.slice_type == H264_SLICE_TYPE_B):
				self.resize_ref_list(1)
				for x in sl.list1:
					self.log(f"list1: {x}")

	def get_free_pic(self):
		ctx = self.ctx; sl = self.ctx.active_sl

		# macOS reference list pooling algo. took me too long
		for pic in ctx.dpb_pool:
			if (pic.flags & H264_FRAME_FLAG_UNUSED): # fill pool at init / drain by poc order sorted at IDR
				pic.flags &= ~(H264_FRAME_FLAG_UNUSED)
				return pic

		cand = None
		ctx.dpb_pool = sorted(ctx.dpb_pool, key=lambda x:x.poc)
		for pic in ctx.dpb_pool:
			if (not (pic.flags & H264_FRAME_FLAG_OUTPUT)):
				cand = pic  # return lowest poc
				break
		if (cand == None):
			raise RuntimeError("failed to find free pic")

		if (sl.nal_unit_type == H264_NAL_SLICE_IDR):
			for pic in ctx.dpb_pool:
				if (not pic.idx == cand.idx):
					pic.flags |= H264_FRAME_FLAG_UNUSED
			ctx.dpb_list = []  # clear DPB on IDR

		return cand

	def get_free_sps_pic(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		for pic in ctx.sps_pool:
			if (pic.flags & H264_FRAME_FLAG_UNUSED): # fill pool at init
				pic.flags &= ~(H264_FRAME_FLAG_UNUSED)
				return pic

		cand = None
		pic = sorted([pic for pic in ctx.sps_pool if not (pic.flags & H264_FRAME_FLAG_LONG_REF)], key=lambda pic: pic.access_idx)[0]
		pic.flags &= ~(H264_FRAME_FLAG_SHORT_REF)
		for pic in ctx.sps_pool:
			if (not (pic.flags & (H264_FRAME_FLAG_SHORT_REF | H264_FRAME_FLAG_LONG_REF))):
				cand = pic
				break
		if (cand == None):
			raise RuntimeError("failed to find free pic")

		if (sl.nal_unit_type == H264_NAL_SLICE_IDR):
			for pic in ctx.sps_pool:
				if (pic.idx > cand.idx):
					pic.flags &= ~(H264_FRAME_FLAG_LONG_REF)

		return cand

	def init_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		sps = ctx.get_sps(sl)

		sl.pic = self.get_free_pic()
		sl.pic.flags |= H264_FRAME_FLAG_OUTPUT
		sl.pic.sps_pic = self.get_free_sps_pic()
		sl.pic.sps_pic.flags |= H264_FRAME_FLAG_SHORT_REF
		sl.pic.sps_idx = sl.pic.sps_pic.idx
		sl.pic.sps_pic.access_idx = ctx.access_idx

		if (sl.field_pic_flag):
			sl.pic.pic_num = (2 * sl.frame_num) + 1
			ctx.max_pic_num = 1 << (sps.log2_max_frame_num_minus4 + 4 + 1)
			raise NotImplementedError("top/bottom fields not supported by hardware.")
		else:
			sl.pic.pic_num = sl.frame_num
			ctx.max_pic_num = 1 << (sps.log2_max_frame_num_minus4 + 4)

		sl.pic.frame_num_wrap = sl.frame_num  # I think it's the same?
		if (sps.gaps_in_frame_num_value_allowed_flag):
			raise NotImplementedError("frame num gaps found. pls send sample.")

		poc_lsb = sl.pic_order_cnt_lsb
		if (sps.pic_order_cnt_type == 0):
			max_poc_lsb = 1 << (sps.log2_max_pic_order_cnt_lsb_minus4 + 4)
			if (ctx.prev_poc_lsb < 0):
				ctx.prev_poc_lsb = poc_lsb

			if ((poc_lsb < ctx.prev_poc_lsb) and (ctx.prev_poc_lsb - poc_lsb >= max_poc_lsb // 2)):
				poc_msb = ctx.prev_poc_msb + max_poc_lsb
			elif ((poc_lsb > ctx.prev_poc_lsb) and (ctx.prev_poc_lsb - poc_lsb < -max_poc_lsb // 2)):
				poc_msb = ctx.prev_poc_msb - max_poc_lsb
			else:
				poc_msb = ctx.prev_poc_msb
		else:
			raise NotImplementedError("pic_order_cnt_type (%d)" % (sps.pic_order_cnt_type))
		ctx.poc_msb = poc_msb
		sl.pic.poc = poc_msb + poc_lsb
		sl.pic.access_idx = ctx.access_idx
		self.construct_ref_list()

	def finish_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		sps = ctx.get_sps(sl)

		if ((sl.nal_unit_type == H264_NAL_SLICE_IDR) or (sl.nal_ref_idc != 0)):
			self.log(f"Adding pic to DPB {sl.pic}")
			sl.pic.flags |= H264_FRAME_FLAG_SHORT_REF
			ctx.dpb_list.append(sl.pic)

		if ((sl.nal_unit_type != H264_NAL_SLICE_IDR) and (sl.nal_ref_idc == 0)):
			# non reference picture
			sl.pic.flags &= ~(H264_FRAME_FLAG_OUTPUT | H264_FRAME_FLAG_SHORT_REF)

		if (sl.nal_ref_idc):
			if (sl.nal_unit_type == H264_NAL_SLICE_IDR) or (sl.adaptive_ref_pic_marking_mode_flag == 0):
				if (len(ctx.dpb_list) > max(sps.max_num_ref_frames, 1)):
					short_refs = [pic for pic in ctx.dpb_list if pic.flags & H264_FRAME_FLAG_SHORT_REF]
					if (len(short_refs) > 0):
						pic = sorted(short_refs, key=lambda pic: pic.access_idx)[0]
						self.log(f"Removing oldest ref {pic}")
						pic.flags &= ~(H264_FRAME_FLAG_OUTPUT | H264_FRAME_FLAG_SHORT_REF)
			else:
				for i,opcode in enumerate(sl.memory_management_control_operation):
					if (opcode == H264_MMCO_END):
						break

					elif (opcode == H264_MMCO_FORGET_SHORT):
						pic_num_diff = sl.mmco_short_args[i] + 1  # abs_diff_pic_num_minus1
						pic_num = sl.pic.pic_num - pic_num_diff
						pic_num &= ctx.max_frame_num - 1
						for pic in ctx.dpb_list:
							if (pic.pic_num == pic_num):
								self.log(f"MMCO: Removing short {pic}")
								assert(pic.flags & H264_FRAME_FLAG_SHORT_REF)
								pic.flags &= ~(H264_FRAME_FLAG_OUTPUT | H264_FRAME_FLAG_SHORT_REF)

					elif (opcode == H264_MMCO_FORGET_LONG):
						long_term_pic_num = sl.mmco_long_args[i]
						for pic in ctx.dpb_list:
							if (pic.pic_num == long_term_pic_num):
								self.log(f"MMCO: Removing long {pic}")
								assert(pic.flags & H264_FRAME_FLAG_LONG_REF)
								pic.flags &= ~(H264_FRAME_FLAG_OUTPUT | H264_FRAME_FLAG_LONG_REF)

					elif (opcode == H264_MMCO_SHORT_TO_LONG):
						long_term_frame_idx = sl.mmco_long_args[i]
						pic_num_diff = sl.mmco_short_args[i] + 1  # abs_diff_pic_num_minus1
						pic_num = sl.pic.pic_num - pic_num_diff
						pic_num &= ctx.max_frame_num - 1
						for pic in ctx.sps_pool:
							pic.flags &= ~(H264_FRAME_FLAG_LONG_REF)
						for pic in ctx.dpb_list:
							if (pic.pic_num == pic_num):
								self.log(f"MMCO: Short to long {pic}")
								assert(pic.flags & H264_FRAME_FLAG_SHORT_REF)
								pic.flags &= ~(H264_FRAME_FLAG_SHORT_REF)
								pic.flags |= H264_FRAME_FLAG_LONG_REF
								pic.pic_num = long_term_frame_idx
								pic.sps_pic.pic_num = long_term_frame_idx
								pic.sps_pic.flags |= H264_FRAME_FLAG_LONG_REF

					elif (opcode == H264_MMCO_FORGET_LONG_MAX):
						ctx.max_lt_idx = sl.mmco_long_args[i] - 1  # max_long_term_frame_idx_plus1
						for pic in ctx.dpb_list:
							if ((pic.flags & H264_FRAME_FLAG_LONG_REF) and (pic.pic_num >= ctx.max_lt_idx)):
								self.log(f"MMCO: Removing long max {pic}")
								assert(pic.flags & H264_FRAME_FLAG_LONG_REF)
								pic.flags &= ~(H264_FRAME_FLAG_LONG_REF)
								pic.sps_pic.flags &= ~(H264_FRAME_FLAG_LONG_REF)
					else:
						raise ValueError("opcode %d not implemented. probably LT ref. pls send sample" % (opcode))

		ctx.dpb_list = [pic for pic in ctx.dpb_list if (pic.flags & H264_FRAME_FLAG_OUTPUT)]

		ctx.prev_poc_lsb = sl.pic_order_cnt_lsb
		ctx.prev_poc_msb = ctx.poc_msb
