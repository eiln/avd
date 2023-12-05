#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..decoder import AVDDecoder, AVDOutputFormat
from ..utils import *
from .fp import AVDH264V3FrameParams
from .halv3 import AVDH264HalV3
from .parser import AVDH264Parser
from .types import *
from math import sqrt
from dataclasses import dataclass

class AVDH264Ctx(dotdict):
	pass

@dataclass
class AVDH264Picture:
	idx: int
	addr: int
	pic_num: int
	poc: int
	frame_num_wrap: int
	flags: int

	def __repr__(self):
		return f"[idx: {str(self.idx).rjust(2)} addr: {hex(self.addr >> 7).ljust(2+5)} pic_num: {str(self.pic_num).rjust(2)} poc: {str(self.poc).rjust(3)} fn: {str(self.frame_num_wrap).rjust(2)} flags: {format(self.flags, '010b')}]"

	def unref(self):
		self.flags = 0

class AVDH264Decoder(AVDDecoder):
	def __init__(self):
		super().__init__(AVDH264Parser, AVDH264HalV3, AVDH264V3FrameParams)
		self.mode = "h264"

	def get_pps(self, sl):
		return self.ctx.pps_list[sl.pic_parameter_set_id]

	def get_sps_id(self, sl):
		return self.get_pps(sl).seq_parameter_set_id

	def get_sps(self, sl):
		return self.ctx.sps_list[self.get_sps_id(sl)]

	def new_context(self, sps_list, pps_list):
		self.ctx = AVDH264Ctx()
		ctx = self.ctx
		ctx.sps_list = sps_list
		ctx.pps_list = pps_list

		ctx.access_idx = 0
		ctx.width = -1
		ctx.height = -1
		ctx.active_sl = None
		ctx.cur_sps_id = -1

		ctx.last_p_sps_tile_idx = 0
		ctx.prev_poc_lsb = 0
		ctx.prev_poc_msb = 0
		ctx.dpb_list = []
		ctx.dpb_pool = []

	def refresh(self, sl):
		self.refresh_sps(sl)
		self.realloc_rbsp_size(sl)

	def refresh_sps(self, sl):
		ctx = self.ctx
		sps_id = self.get_sps_id(sl)
		if (sps_id == ctx.cur_sps_id):
			return
		sps = ctx.sps_list[sps_id]

		width = ((sps.pic_width_in_mbs_minus1 + 1) * 16) - (sps.frame_crop_right_offset * 2) - (sps.frame_crop_left_offset * 2)
		height = ((2 - sps.frame_mbs_only_flag) * (sps.pic_height_in_map_units_minus1 + 1) * 16) - (sps.frame_crop_bottom_offset * 2) - (sps.frame_crop_top_offset * 2)

		ctx.orig_width = width
		ctx.orig_height = height
		if (width & 15):
			width = round_up(width, 16)
		if (height & 15):
			height = round_up(height, 16)
		if ((width != ctx.orig_width) or (height != ctx.orig_height)):
			self.log("dimensions changed from %dx%d -> %dx%d" % (ctx.width, ctx.height, width, height))
		ctx.width = width
		ctx.height = height

		assert((64 <= width and width <= 4096) and (64 <= height and height <= 4096)) # hardware caps
		assert(not(width & 15) and not(height & 15)) # hardware caps
		ctx.max_frame_num = 1 << (sps.log2_max_frame_num_minus4 + 4)

		width_mbs = (sps.pic_width_in_mbs_minus1 + 1)
		height_mbs = (2 - sps.frame_mbs_only_flag) * (sps.pic_height_in_map_units_minus1 + 1)
		assert(width_mbs == (ctx.orig_width + 15) // 16)
		assert(height_mbs == (ctx.orig_height + 15) // 16)

		ctx.fmt = AVDOutputFormat(
			in_width=(round_up(ctx.width, 64) >> 4) << 4,
			in_height=ctx.height,
			out_width=ctx.orig_width,
			out_height=ctx.orig_height,
			chroma=sps.chroma_format_idc,
		)
		ctx.fmt.x0 = 0
		ctx.fmt.x1 = ctx.fmt.out_width  # TODO vui frame crop
		ctx.fmt.y0 = 0
		ctx.fmt.y1 = ctx.fmt.out_height
		self.log(ctx.fmt)
		assert(ctx.fmt.in_width >= ctx.fmt.out_width)
		assert(ctx.fmt.in_height >= ctx.fmt.out_height)

		level = [level for level in h264_levels if level[1] == sps.level_idc][-1]
		ctx.max_dpb_frames = min((level[5]) // (width_mbs * height_mbs), 16) # max_dpb_mbs
		ctx.rvra_count = ctx.max_dpb_frames + 1 + 1  # all refs + IDR + current
		assert((width_mbs * height_mbs) <= level[4]) # MaxFS
		assert(width_mbs <= sqrt(level[4] * 8))
		assert(height_mbs <= sqrt(level[4] * 8))
		ctx.cur_sps_id = sps_id
		self.allocate_buffers()

	def allocate_buffers(self):
		ctx = self.ctx
		# matching macOS allocations makes for easy diffs
		# see tools/dims264.py experiment
		sps = ctx.sps_list[ctx.cur_sps_id]
		assert((sps.chroma_format_idc == H264_CHROMA_IDC_420) or
		       (sps.chroma_format_idc == H264_CHROMA_IDC_422))

		self.reset_allocator()
		ctx.inst_fifo_count = 7
		ctx.inst_fifo_idx = 0  # no FIFO scheduling for single-VP revisions
		ctx.inst_fifo_addrs = [0 for n in range(ctx.inst_fifo_count)]
		self.allocator_move_up(0x4000)
		for n in range(ctx.inst_fifo_count):
			ctx.inst_fifo_addrs[n] = self.range_alloc(0x100000, pad=0x4000, name="inst_fifo%d" % n)
		ctx.inst_fifo_iova = ctx.inst_fifo_addrs[ctx.inst_fifo_idx]

		rvra_total_size = self.calc_rvra(is_422=sps.chroma_format_idc == H264_CHROMA_IDC_422)
		self.allocator_move_up(0x734000)
		ctx.rvra_base_addrs = [0 for n in range(ctx.rvra_count)]
		ctx.rvra_base_addrs[0] = self.range_alloc(rvra_total_size, pad=0x100, name="rvra0")

		ctx.luma_size = ctx.fmt.in_width * ctx.fmt.in_height
		ctx.y_addr = self.range_alloc(ctx.luma_size, name="disp_y")
		ctx.chroma_size = ctx.fmt.in_width * ctx.fmt.in_height
		if (sps.chroma_format_idc == H264_CHROMA_IDC_420):
			ctx.chroma_size //= 2
		ctx.uv_addr = self.range_alloc(ctx.chroma_size, name="disp_uv")

		ctx.slice_data_size = min((((round_up(ctx.width, 32) - 1) * (round_up(ctx.height, 32) - 1) // 0x8000) + 2), 0xff) * 0x4000
		ctx.slice_data_addr = self.range_alloc(ctx.slice_data_size, align=0x4000, padb4=0x4000, name="slice_data")

		ctx.sps_tile_count = 24
		ctx.sps_tile_addrs = [0 for n in range(ctx.sps_tile_count)]
		sps_tile_size = (((ctx.width - 1) * (ctx.height - 1) // 0x10000) + 2) * 0x4000
		for n in range(ctx.sps_tile_count):
			ctx.sps_tile_addrs[n] = self.range_alloc(sps_tile_size, name="sps_tile%d" % n)

		pps_tile_count = 5
		ctx.pps_tile_addrs = [0 for n in range(pps_tile_count)]
		for n in range(pps_tile_count):
			size = (((ctx.width >> 11) + 1) * 0x4000) + 0x4000
			ctx.pps_tile_addrs[n] = self.range_alloc(size, name="pps_tile%d" % n)

		for n in range(ctx.rvra_count - 1):
			ctx.rvra_base_addrs[n + 1] = self.range_alloc(rvra_total_size, name="rvra1_%d" % n)
		self.dump_ranges()

		ctx.dpb_pool = []
		for i in range(ctx.rvra_count):
			pic = AVDH264Picture(addr=ctx.rvra_base_addrs[i], idx=i, pic_num=-1, poc=-1, frame_num_wrap=-1, flags=H264_FRAME_FLAG_UNUSED)
			ctx.dpb_pool.append(pic)
			self.log(f"DPB Pool: {pic}")

	def setup(self, path, num=0, nal_stop=0, **kwargs):
		sps_list, pps_list, slices = self.parser.parse(path, num, nal_stop, **kwargs)
		self.new_context(sps_list, pps_list)
		# realistically we'd have the height/width as metadata w/o relying on sps
		return slices

	def get_short_ref_by_num(self, lst, pic_num):
		cands = [pic for pic in lst if pic and pic.pic_num == pic_num]
		assert(len(cands) == 1)
		return cands[0]

	def modify_ref_list(self, lst, lx):
		ctx = self.ctx; sl = self.ctx.active_sl
		assert(sl[f"ref_pic_list_modification_flag_l{lx}"])
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

				sref = self.get_short_ref_by_num(sl.pic.short_refs, pred)
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
				raise NotImplementedError("LT refs not support yet")

		return lst[:num_ref_idx_lx_active_minus1 + 1]

	def construct_ref_list_p(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		short_refs = [pic for pic in ctx.dpb_list if pic.flags & H264_FRAME_FLAG_SHORT_REF]
		short_refs = sorted(short_refs, key=lambda pic: pic.frame_num_wrap, reverse=True)
		for ref in short_refs:
			self.log(f"P: ST Refs: {ref}")
		sl.pic.short_refs = short_refs
		list0 = short_refs
		if (sl.ref_pic_list_modification_flag_l0):
			list0 = self.modify_ref_list(list0, 0)
		sl.pic.list0 = list0

	def construct_ref_list_b(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		short_refs = [pic for pic in ctx.dpb_list if pic.flags & H264_FRAME_FLAG_SHORT_REF]
		short_refs = sorted(short_refs, key=lambda pic: pic.poc, reverse=True)
		for ref in short_refs:
			self.log(f"B: ST Refs: {ref}")
		sl.pic.short_refs = short_refs
		list0 = sorted([pic for pic in short_refs if pic.poc < sl.pic.poc], key=lambda pic: pic.poc, reverse=True)
		list1 = sorted([pic for pic in short_refs if pic.poc > sl.pic.poc], key=lambda pic: pic.poc)
		if (sl.ref_pic_list_modification_flag_l0):
			list0 = self.modify_ref_list(list0, 0)
		if (sl.ref_pic_list_modification_flag_l1):
			list1 = self.modify_ref_list(list1, 1)
		sl.pic.list0 = list0
		sl.pic.list1 = list1

	def construct_ref_list(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		if (sl.slice_type == H264_SLICE_TYPE_P):
			self.construct_ref_list_p()
		elif (sl.slice_type == H264_SLICE_TYPE_B):
			self.construct_ref_list_b()

	def get_next_pic(self):
		ctx = self.ctx; sl = self.ctx.active_sl

		# macOS reference list pooling algo. took me too long
		cand = None

		for pic in ctx.dpb_pool:
			if (pic.flags & H264_FRAME_FLAG_UNUSED): # fill pool at init
				pic.flags &= ~(H264_FRAME_FLAG_UNUSED)
				return pic
			if (pic.flags & H264_FRAME_FLAG_DRAIN):  # drain by poc order sorted at IDR
				pic.flags &= ~(H264_FRAME_FLAG_DRAIN)
				return pic

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
					pic.flags |= H264_FRAME_FLAG_DRAIN
			ctx.dpb_list = []  # clear DPB on IDR

		return cand

	def init_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		self.refresh(sl)

		sl.pic = self.get_next_pic()
		sl.pic.flags |= H264_FRAME_FLAG_OUTPUT | H264_FRAME_FLAG_SHORT_REF
		sps = self.get_sps(sl)

		if (sl.field_pic_flag):
			sl.pic.field = H264_FIELD_BOTTOM if sl.bottom_field_flag else H264_FIELD_BOTTOM
			sl.pic.pic_num = (2 * sl.frame_num) + 1
			ctx.max_pic_num = 1 << (sps.log2_max_frame_num_minus4 + 4 + 1)
			raise NotImplementedError("top/bottom fields not supported. pls send sample")
		else:
			sl.pic.field = H264_FIELD_FRAME
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
		sl.pic.poc_lsb = poc_lsb
		sl.pic.poc_msb = poc_msb
		sl.pic.poc = poc_msb + poc_lsb
		sl.pic.access_idx = ctx.access_idx

		self.construct_ref_list()

	def finish_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl

		if (sl.nal_unit_type == H264_NAL_SLICE_IDR) or (sl.nal_ref_idc != 0):
			self.log(f"Adding pic to DPB {sl.pic}")
			ctx.dpb_list.append(sl.pic)

		if (sl.nal_unit_type != H264_NAL_SLICE_IDR) and (sl.nal_ref_idc == 0):
			sl.pic.unref()

		if (sl.nal_ref_idc):
			if (sl.nal_unit_type == H264_NAL_SLICE_IDR) or (sl.adaptive_ref_pic_marking_mode_flag == 0):
				if (len(ctx.dpb_list) > self.get_sps(sl).max_num_ref_frames):
					oldest = sorted(ctx.dpb_list, key=lambda pic: pic.access_idx)[0]
					self.log(f"Removing oldest ref {oldest}")
					oldest.unref()
			else:
				for i,opcode in enumerate(sl.memory_management_control_operation):
					if (opcode == H264_MMCO_END): break
					if (opcode == H264_MMCO_SHORT2UNUSED):
						pic_num_diff = sl.mmco_short_args[i] + 1  # abs_diff_pic_num_minus1
						pic_num = sl.pic.pic_num - pic_num_diff
						pic_num &= ctx.max_frame_num - 1
						for pic in ctx.dpb_list:
							if (pic.pic_num == pic_num):
								self.log(f"MMCO: Removing short {pic}")
								pic.unref()
					else:
						raise ValueError("opcode %d not implemented. probably LT ref. pls send sample" % (opcode))
		ctx.dpb_list = [pic for pic in ctx.dpb_list if (pic.flags & H264_FRAME_FLAG_OUTPUT)]

		ctx.prev_poc_lsb = sl.pic.poc_lsb
		ctx.prev_poc_msb = sl.pic.poc_msb

		if (sl.slice_type == H264_SLICE_TYPE_P):
			ctx.last_p_sps_tile_idx = ctx.access_idx % ctx.sps_tile_count
		self.ctx.access_idx += 1
