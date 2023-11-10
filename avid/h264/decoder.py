#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from ..decoder import AVDDecoder
from ..utils import *
from .fp import AVDH264V3FrameParams
from .halv3 import AVDH264HalV3
from .parser import AVDH264Parser
from .types import *
from math import sqrt

class AVDH264Ctx(dotdict):
	pass

class AVDH264Picture(dotdict):
	def __repr__(self):
		return f"[addr: {hex(self.addr >> 7).ljust(2+5)} pic_num: {str(self.pic_num).rjust(2)} poc: {str(self.poc).rjust(3)} fn: {str(self.frame_num_wrap).rjust(2)} idx: {str(self.idx).rjust(2)}]"

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
		ctx.unused_refs = []
		ctx.drain_list = []
		ctx.rvra_pool_count = 0

		ctx.inst_fifo_count = 6
		ctx.inst_fifo_idx = 0

	def refresh(self, sl):
		ctx = self.ctx
		sps_id = self.get_sps_id(sl)
		if (sps_id == ctx.cur_sps_id):
			return
		sps = ctx.sps_list[sps_id]

		width = ((sps.pic_width_in_mbs_minus1 + 1) * 16) - (sps.frame_crop_right_offset * 2) - (sps.frame_crop_left_offset * 2)
		height = ((2 - sps.frame_mbs_only_flag) * (sps.pic_height_in_map_units_minus1 + 1) * 16) - (sps.frame_crop_bottom_offset * 2) - (sps.frame_crop_top_offset * 2)
		if ((width == ctx.width) and (height == ctx.height)):
			return

		self.log("dimensions changed from %dx%d -> %dx%d" % (ctx.width, ctx.height, width, height))
		ctx.width = width
		ctx.height = height
		assert((64 <= width and width <= 4096) and (64 <= height and height <= 4096)) # hardware caps
		assert(not(width & 15) and not(height & 15)) # hardware caps
		ctx.max_frame_num = 1 << (sps.log2_max_frame_num_minus4 + 4)

		width_mbs = (ctx.width + 15) // 16
		height_mbs = (ctx.height + 15) // 16
		assert(width_mbs == (sps.pic_width_in_mbs_minus1 + 1))
		assert(height_mbs == (sps.pic_height_in_map_units_minus1 + 1))

		level = [level for level in h264_levels if level[1] == sps.level_idc][0]
		ctx.max_dpb_frames = min((level[5]) // (width_mbs * height_mbs), 16) # max_dpb_mbs
		#assert((width_mbs * height_mbs) <= level[4]) # MaxFS
		assert(width_mbs <= sqrt(level[4] * 8))
		assert(height_mbs <= sqrt(level[4] * 8))
		ctx.cur_sps_id = sps_id
		self.allocate()

	def allocate(self):
		ctx = self.ctx
		# matching macOS allocations makes for easy diffs
		# see tools/dims264.py experiment

		# constants
		ctx.inst_fifo_iova = 0x4000
		ctx.inst_fifo_size = 0x100000
		ctx.pps_tile_count = 5  # just random work buffers; they call it sps/pps for non-mpeg codecs too
		ctx.pps_tile_size = 0x8000
		ctx.sps_tile_count = 24  # again, nothing to do with sps; just a name for work buf group 2
		ctx.rvra0_addr = 0x734000

		if (ctx.width == 128 and ctx.height == 64):
			ctx.slice_data_size = 0x8000
			ctx.sps_tile_size = 0x8000
			ctx.rvra_total_size = 0x8000
		elif (ctx.width == 1024 and ctx.height == 512):
			ctx.slice_data_size = 0x44000
			ctx.sps_tile_size = 0x24000
			ctx.rvra_total_size = 0xfc000
		else:
			# worst case, oops
			ctx.slice_data_size = 0x10000  # this is so trivial but I can't figure it out
			#dims.sps_tile_size = 0x4000 * ((clog2(dims.width) - 6) * (clog2(dims.height) - 6))
			ctx.sps_tile_size = 0x40000
			ctx.rvra_total_size = 0x1000000

		ctx.y_addr = ctx.rvra0_addr + ctx.rvra_total_size + 0x100

		# Pixel/disp buf != buf stored in DPB as reference.
		# Refs are tiled/scaled smaller than the orig. They call it "rvra scaler buffer".
		# Searching "rvra" "scaler" "apple" led to US10045089B2,
		# "video resolution adaptation (VRA), reference VRA (RVRA)" which answers little
		scale = min(pow2div(ctx.height), pow2div(ctx.width))
		if (scale >= 32):
			luma_size = ctx.height * ctx.width
		else:   # scale to 64 if it's <32, but leave it if it's >=32 (?)
			luma_size = round_up(ctx.width, 64) * round_up(ctx.height, 64)
		ctx.uv_addr = ctx.y_addr + luma_size

		scale = min(pow2div(ctx.height), pow2div(ctx.width))
		if (scale >= 32):
			chroma_size = ctx.height * ctx.width // 2
		else:
			chroma_size = round_up(ctx.height * ctx.width // 2, 0x4000)
		ctx.slice_data_addr = round_up(ctx.uv_addr + chroma_size, 0x4000) + 0x4000

		ctx.sps_tile_addr = ctx.slice_data_addr + ctx.slice_data_size
		ctx.pps_tile_addr = ctx.sps_tile_addr + (ctx.sps_tile_size * ctx.sps_tile_count)
		ctx.rvra1_addr = ctx.pps_tile_addr + (ctx.pps_tile_size * ctx.pps_tile_count)

		ctx.rvra_size0 = (round_up(ctx.height, 32) * round_up(ctx.width, 32)) + ((round_up(ctx.height, 32) * round_up(ctx.width, 32)) // 4)
		ctx.rvra_size2 = ctx.rvra_size0 // 2
		ctx.rvra_size1 = ((nextpow2(ctx.height) // 32) * nextpow2(ctx.width))
		ctx.rvra_size3 = ctx.rvra_total_size - ctx.rvra_size2 - ctx.rvra_size1 - ctx.rvra_size0
		ctx.rvra_count = ctx.max_dpb_frames + 1 + 1

	def setup(self, path, **kwargs):
		sps_list, pps_list, slices = self.parser.parse(path)
		self.new_context(sps_list, pps_list)
		# realistically we'd have the height/width as metadata w/o relying on sps
		self.refresh(slices[0])
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
		ctx = self.ctx; sl = self.ctx.active_sl # python woes
		short_refs = [pic for pic in ctx.dpb_list if pic.type == H264_REF_ST]
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
		short_refs = [pic for pic in ctx.dpb_list if pic.type == H264_REF_ST]
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

	def get_rvra_addr(self, idx):
		ctx = self.ctx
		if (idx % ctx.rvra_count == 0): return ctx.rvra0_addr
		else: return ctx.rvra1_addr + (((idx % ctx.rvra_count) - 1) * ctx.rvra_total_size)

	def get_next_rvra(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		# rvra pooling algo. took me too long
		index = 0
		if (ctx.rvra_pool_count < ctx.rvra_count): # fill pool at init
			index = ctx.rvra_pool_count
			ctx.rvra_pool_count += 1
		elif (sl.nal_unit_type == H264_NAL_SLICE_IDR):
			pool = ctx.unused_refs + ctx.dpb_list # gather refs
			cand = sorted(pool, key=lambda x: x.poc)[0]
			index = cand.idx
			pool = [x for x in pool if x != cand]
			ctx.drain_list = sorted(pool, key=lambda x:x.poc)
			ctx.dpb_list = [] # clear DPB on IDR
		elif (len(ctx.drain_list)):
			cand = ctx.drain_list[0] # drain by initial sorted poc order
			index = cand.idx
			ctx.unused_refs = [x for x in ctx.unused_refs if x != cand]
			ctx.drain_list = ctx.drain_list[1:]
		else:
			min_poc = sorted(ctx.unused_refs, key=lambda x: x.poc)[0].poc
			cand = [x for x in ctx.unused_refs if x.poc == min_poc][0]
			index = cand.idx
			ctx.unused_refs = [x for x in ctx.unused_refs if x != cand]
		return index

	def init_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl
		self.refresh(sl)

		sl.pic = AVDH264Picture()
		sl.pic.type = H264_REF_ST
		sps = self.get_sps(sl)

		if (sl.field_pic_flag):
			sl.pic.field = H264_FIELD_BOTTOM if sl.bottom_field_flag else H264_FIELD_BOTTOM
			sl.pic.pic_num = (2 * sl.frame_num) + 1
			ctx.max_pic_num = 1 << (sps.log2_max_frame_num_minus4 + 4 + 1)
			raise NotImplementedError("top/bottom fields not yet supported")
		else:
			sl.pic.field = H264_FIELD_FRAME
			sl.pic.pic_num = sl.frame_num
			ctx.max_pic_num = 1 << (sps.log2_max_frame_num_minus4 + 4)

		sl.pic.frame_num = sl.frame_num
		sl.pic.frame_num_wrap = sl.pic.frame_num
		assert(sps.gaps_in_frame_num_value_allowed_flag == 0) # TODO

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

		sl.pic.idx = self.get_next_rvra()
		sl.pic.addr = self.get_rvra_addr(sl.pic.idx)

		self.construct_ref_list()

	def finish_slice(self):
		ctx = self.ctx; sl = self.ctx.active_sl

		if (sl.nal_unit_type == H264_NAL_SLICE_IDR) or (sl.nal_ref_idc != 0):
			self.log(f"Adding pic to dpb {sl.pic}")
			ctx.dpb_list.append(sl.pic)
			ctx.unused_refs = [i for i in ctx.unused_refs if i.addr != sl.pic.addr]

		if (sl.nal_unit_type != H264_NAL_SLICE_IDR) and (sl.nal_ref_idc == 0):
			ctx.unused_refs.append(sl.pic)

		if (sl.nal_unit_type == H264_NAL_SLICE_IDR) or (sl.adaptive_ref_pic_marking_mode_flag == 0):
			if (len(ctx.dpb_list) > self.get_sps(sl).max_num_ref_frames):
				oldest = sorted(ctx.dpb_list, key=lambda pic: pic.access_idx)[0]
				self.log(f"ADPT: removing oldest ref {oldest}")
				ctx.dpb_list = [x for x in ctx.dpb_list if x != oldest]
				ctx.unused_refs.append(oldest)
		else:
			for pic_num_diff in sl.mmco_forget_short:
				if (pic_num_diff == None): break
				pic_num = sl.pic.pic_num - (pic_num_diff + 1)
				pic_num &= ctx.max_frame_num - 1
				pic = [x for x in ctx.dpb_list if x.pic_num == pic_num]
				assert(len(pic) == 1)
				pic = pic[0]
				self.log(f"MMCO: removing short {pic}")
				ctx.dpb_list = [x for x in ctx.dpb_list if x.pic_num != pic_num]
				ctx.unused_refs.append(pic)

		ctx.prev_poc_lsb = sl.pic.poc_lsb
		ctx.prev_poc_msb = sl.pic.poc_msb

		if (sl.slice_type == H264_SLICE_TYPE_P):
			ctx.last_p_sps_tile_idx = ctx.access_idx % ctx.sps_tile_count
		self.ctx.access_idx += 1
