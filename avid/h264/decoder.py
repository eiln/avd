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
	def get_pps(self, sl):
		return self.pps_list[sl.pic_parameter_set_id]

	def get_sps(self, sl):
		return self.sps_list[self.get_pps(sl).seq_parameter_set_id]

	def rvra_offset(self, idx):
		if   (idx == 0): return self.rvra_size0
		elif (idx == 1): return 0
		elif (idx == 2): return self.rvra_size0 + self.rvra_size1 + self.rvra_size2
		elif (idx == 3): return self.rvra_size0 + self.rvra_size1
		raise ValueError("invalid rvra group (%d)" % idx)

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

	def __repr__(self):
		return f"[idx: {str(self.idx).rjust(2)} addr: {hex(self.addr >> 7).ljust(2+5)} pic_num: {str(self.pic_num).rjust(2)} poc: {str(self.poc).rjust(3)} fn: {str(self.frame_num_wrap).rjust(2)} flags: {format(self.flags, '010b')}]"

class AVDH264Decoder(AVDDecoder):
	def __init__(self):
		super().__init__(AVDH264Parser, AVDH264HalV3, AVDH264V3FrameParams)
		self.mode = "h264"

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

		ctx.prev_poc_lsb = 0
		ctx.prev_poc_msb = 0
		ctx.max_lt_idx = -1
		ctx.dpb_list = []
		ctx.dpb_pool = []

	def refresh(self, sl):
		self.refresh_sps(sl)
		self.realloc_rbsp_size(sl)

	def refresh_sps(self, sl):
		ctx = self.ctx
		pps = ctx.get_pps(sl)
		sps_id = pps.seq_parameter_set_id
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

		# Hardware caps
		assert((64 <= width and width <= 4096) and (64 <= height and height <= 4096))
		assert(not(width & 15) and not(height & 15))
		assert((sps.chroma_format_idc == H264_CHROMA_IDC_420) or
		       (sps.chroma_format_idc == H264_CHROMA_IDC_422))
		if (sps.bit_depth_luma_minus8 != sps.bit_depth_chroma_minus8):
			raise ValueError("Haven't tested")

		stride = round_up(sps.bit_depth_luma_minus8 + 8, 8) // 8
		ctx.fmt = AVDOutputFormat(
			in_width         = ((round_up(ctx.width * stride, 64) >> 4) << 4),
			in_height        = (round_up(ctx.height, 16) >> 4) << 4,
			out_width        = ctx.orig_width,
			out_height       = ctx.orig_height,
			chroma           = sps.chroma_format_idc,
			bitdepth_luma    = sps.bit_depth_luma_minus8 + 8,
			bitdepth_chroma  = sps.bit_depth_chroma_minus8 + 8,
		)
		ctx.fmt.x0 = 0
		ctx.fmt.x1 = ctx.fmt.out_width  # TODO vui frame crop
		ctx.fmt.y0 = 0
		ctx.fmt.y1 = ctx.fmt.out_height
		self.log(ctx.fmt)
		assert(ctx.fmt.in_width >= ctx.fmt.out_width)
		assert(ctx.fmt.in_height >= ctx.fmt.out_height)

		ctx.max_frame_num = 1 << (sps.log2_max_frame_num_minus4 + 4)
		if (sps.vui_parameters_present_flag):
			ctx.num_reorder_frames = sps.num_reorder_frames + 1
		else:
			ctx.num_reorder_frames = sps.max_num_ref_frames

		width_mbs = (sps.pic_width_in_mbs_minus1 + 1)
		height_mbs = (2 - sps.frame_mbs_only_flag) * (sps.pic_height_in_map_units_minus1 + 1)
		assert(width_mbs == (ctx.orig_width + 15) // 16)  # No interlaced
		assert(height_mbs == (ctx.orig_height + 15) // 16)

		level = [level for level in h264_levels if level[1] == sps.level_idc][-1]
		ctx.max_dpb_frames = min((level[5]) // (width_mbs * height_mbs), 16) # max_dpb_mbs
		ctx.rvra_count = ctx.max_dpb_frames + 1 + 1  # all refs + IDR + current
		assert((width_mbs * height_mbs) <= level[4]) # MaxFS
		assert(width_mbs <= sqrt(level[4] * 8))
		assert(height_mbs <= sqrt(level[4] * 8))
		ctx.cur_sps_id = sps_id
		self.allocate_buffers(sl)

	def allocate_buffers(self, sl):
		ctx = self.ctx
		# matching macOS allocations makes for easy diffs
		# see tools/dims264.py experiment
		sps = ctx.get_sps(sl)

		self.reset_allocator()
		ctx.inst_fifo_count = 7
		ctx.inst_fifo_idx = 0  # no FIFO scheduling for single-VP revisions
		ctx.inst_fifo_addrs = [0 for n in range(ctx.inst_fifo_count)]
		self.allocator_move_up(0x4000)
		for n in range(ctx.inst_fifo_count):
			ctx.inst_fifo_addrs[n] = self.range_alloc(0x100000, pad=0x4000, name="inst_fifo%d" % n)
		ctx.inst_fifo_iova = ctx.inst_fifo_addrs[ctx.inst_fifo_idx]

		rvra_total_size = self.calc_rvra(chroma=sps.chroma_format_idc)
		self.allocator_move_up(0x734000)
		ctx.rvra_base_addrs = [0 for n in range(ctx.rvra_count)]
		ctx.rvra_base_addrs[0] = self.range_alloc(rvra_total_size, name="rvra0")

		ctx.luma_size = ctx.fmt.in_width * ctx.fmt.in_height
		ctx.y_addr = self.range_alloc(ctx.luma_size, padb4=0x100, name="disp_y")
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

		# Intermediate work tile group #0, 5 tiles based on hw cache line i.e. width stride 16
		pps_tile_count = 5
		ctx.pps_tile_addrs = [0 for n in range(pps_tile_count)]
		for n in range(pps_tile_count):
			if (n == 0):
				# Tile #0: I could not tell you what this means, but it's overwritten on intra frames.
				# Worst 4096x4096 case it still uses <0x8000, which we have to anyway to make tests pass
				"""
				0080c000: 04822000 10000000 38000000 38000000 00000000 00880000 00000000 38000000
				0080c020: 38000000 00000000 00880000 00000000 38000000 38000000 00000000 08800007
				0080c040: 02000000 30000000 38000000 00000000 00000000 00000000 00000000 00000000
				"""
				size = 0x8000
			if (n == 1):
				# Tile #1: Y 1x16, Cb 1x8, Cr 1x8 per row
				"""
				00814000: 51515151 51515151 51515151 51515151 5a5a5a5a 5a5a5a5a f0f0f0f0 f0f0f0f0 ] row
				00814020: 51515151 51515151 51515151 51515151 5a5a5a5a 5a5a5a5a f0f0f0f0 f0f0f0f0
				00814040: 51515151 51515151 51515151 51515151 5a5a5a5a 5a5a5a5a f0f0f0f0 f0f0f0f0
				00814060: 51515151 51515151 51515151 51515151 5a5a5a5a 5a5a5a5a f0f0f0f0 f0f0f0f0
				"""
				size = (1*16 + 1*8 + 1*8) * (round_up(ctx.width, 16) // 16)
			elif (n == 2):
				# Tile #2: Y 2x32, Cb 1x32, Cr 1x32 per row
				"""
				0081c000: 51515151 51515151 51515151 51515151 51515151 51515151 51515151 51515151 ] row
				0081c020: 51515151 51515151 51515151 51515151 51515151 51515151 51515151 51515151 ]
				0081c040: 5a5a5a5a 5a5a5a5a 5a5a5a5a 5a5a5a5a 5a5a5a5a 5a5a5a5a 5a5a5a5a 5a5a5a5a ]
				0081c060: f0f0f0f0 f0f0f0f0 f0f0f0f0 f0f0f0f0 f0f0f0f0 f0f0f0f0 f0f0f0f0 f0f0f0f0 ]
				"""
				size = (2*32 + 1*32 + 1*32) * (round_up(ctx.width, 16) // 16)
				# macOS overallocates a lot so we have to do this to make tests pass
				if (ctx.fmt.in_width > 2048):
					size = 0xc000
			elif (n == 3):
				# Tile #3: No idea what this means, I think it's entropy. 32 bytes per row
				"""
				00824000: c0000000 c0000000 00000000 58000000 04000000 00000000 04000000 00000000 ] row
				00824020: c0000000 c0000000 00000000 50000000 04000000 00000000 04000000 00000000
				00824040: 40000000 40000000 00000000 50000000 00000000 00000000 00000000 00000000
				00824060: c0000000 c0000000 00000000 50000000 04000000 00000000 04000000 00000000
				"""
				size = (1*32) * (round_up(ctx.width, 16) // 16)
			elif (n == 4):
				# Tile #4: Ditto. I think it's reference frame entropy.
				"""
				0082c000: c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 ] row
				0082c020: c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 c0000000
				0082c040: 40000000 40000000 40000000 40000000 40000000 40000000 40000000 40000000
				0082c060: c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 c0000000 c0000000
				"""
				size = (1*32) * (round_up(ctx.width, 16) // 16)
			size = max(size, 0x8000)
			ctx.pps_tile_addrs[n] = self.range_alloc(size, align=0x4000, name="pps_tile%d" % n)

		for n in range(ctx.rvra_count - 1):
			ctx.rvra_base_addrs[n + 1] = self.range_alloc(rvra_total_size, align=0x4000, name="rvra1_%d" % n)
		self.dump_ranges()

		ctx.dpb_pool = []
		for i in range(ctx.rvra_count):
			pic = AVDH264Picture(addr=ctx.rvra_base_addrs[i], idx=i, pic_num=-1, poc=-1, frame_num_wrap=-1, flags=H264_FRAME_FLAG_UNUSED, access_idx=-1)
			ctx.dpb_pool.append(pic)
			self.log(f"DPB Pool: {pic}")

	def setup(self, path, num=0, nal_stop=0, **kwargs):
		sps_list, pps_list, slices = self.parser.parse(path, num, nal_stop, **kwargs)
		self.new_context(sps_list, pps_list)
		return slices

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

	def resize_ref_list(self, lx): # 8.4.2.2
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

	def init_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		self.refresh(sl)
		sps = ctx.get_sps(sl)

		sl.pic = self.get_free_pic()
		sl.pic.flags |= H264_FRAME_FLAG_OUTPUT
		sl.pic.sps_idx = ctx.access_idx % ctx.sps_tile_count

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
						for pic in ctx.dpb_list:
							if (pic.pic_num == pic_num):
								self.log(f"MMCO: Short to long {pic}")
								assert(pic.flags & H264_FRAME_FLAG_SHORT_REF)
								pic.flags &= ~(H264_FRAME_FLAG_SHORT_REF)
								pic.flags |= H264_FRAME_FLAG_LONG_REF
								pic.pic_num = long_term_frame_idx

					elif (opcode == H264_MMCO_FORGET_LONG_MAX):
						ctx.max_lt_idx = sl.mmco_long_args[i] - 1  # max_long_term_frame_idx_plus1
						for pic in ctx.dpb_list:
							if ((pic.flags & H264_FRAME_FLAG_LONG_REF) and (pic.pic_num >= ctx.max_lt_idx)):
								self.log(f"MMCO: Removing long max {pic}")
								assert(pic.flags & H264_FRAME_FLAG_LONG_REF)
								pic.flags &= ~(H264_FRAME_FLAG_LONG_REF)

					else:
						raise ValueError("opcode %d not implemented. probably LT ref. pls send sample" % (opcode))

		ctx.dpb_list = [pic for pic in ctx.dpb_list if (pic.flags & H264_FRAME_FLAG_OUTPUT)]

		ctx.prev_poc_lsb = sl.pic_order_cnt_lsb
		ctx.prev_poc_msb = ctx.poc_msb

		self.ctx.access_idx += 1
