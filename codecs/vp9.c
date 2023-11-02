// clang-format off
/*
 * VP9 compatible video decoder
 *
 * Copyright (C) 2013 Ronald S. Bultje <rsbultje gmail com>
 * Copyright (C) 2013 Clément Bœsch <u pkh me>
 *
 * This file is part of FFmpeg.
 *
 * FFmpeg is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * FFmpeg is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with FFmpeg; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>

#include "bs.h"
#include "vp9_data.h"
#include "vp9_shared.h"
#include "vp9.h"

#define vp9_log(a, ...)   printf("[VP9] " a, ##__VA_ARGS__)
#define vp9_field(a, ...) printf("\t" a " = %d\n", ##__VA_ARGS__)

#define VP9_SYNCCODE	    0x498342

// The sign bit is at the end, not the start, of a bit sequence
static inline int get_sbits_inv(struct bitstream *gb, int n)
{
	int v = get_bits(gb, n);
	return get_bits1(gb) ? -v : v;
}

static inline int inv_recenter_nonneg(int v, int m)
{
	if (v > 2 * m)
		return v;
	if (v & 1)
		return m - ((v + 1) >> 1);
	return m + (v >> 1);
}

static int vp9_read_colorspace_details(VP9Context *s)
{
	static const enum AVColorSpace colorspaces[8] = {
		AVCOL_SPC_UNSPECIFIED, AVCOL_SPC_BT470BG, AVCOL_SPC_BT709, AVCOL_SPC_SMPTE170M,
		AVCOL_SPC_SMPTE240M, AVCOL_SPC_BT2020_NCL, AVCOL_SPC_RESERVED, AVCOL_SPC_RGB,
	};
	int bits = s->profile <= 1 ? 0 : 1 + get_bits1(&s->gb); // 0:8, 1:10, 2:12

	s->bpp_index = bits;
	s->s.h.bpp = 8 + bits * 2;
	s->bytesperpixel = (7 + s->s.h.bpp) >> 3;
	s->colorspace = colorspaces[get_bits(&s->gb, 3)];
	if (s->colorspace == AVCOL_SPC_RGB) { // RGB = profile 1
		static const enum AVPixelFormat pix_fmt_rgb[3] = {
			AV_PIX_FMT_GBRP, AV_PIX_FMT_GBRP10, AV_PIX_FMT_GBRP12
		};
		s->ss_h = s->ss_v = 0;
		s->color_range = AVCOL_RANGE_JPEG;
		s->pix_fmt = pix_fmt_rgb[bits];
		if (s->profile & 1) {
			if (get_bits1(&s->gb)) {
				fprintf(stderr, "Reserved bit set in RGB\n");
				return AVERROR_INVALIDDATA;
			}
		} else {
			fprintf(stderr, "RGB not supported in profile %d\n", s->profile);
			return AVERROR_INVALIDDATA;
		}
    } else {
		static const enum AVPixelFormat pix_fmt_for_ss[3][2 /* v */][2 /* h */] = {
			{ { AV_PIX_FMT_YUV444P, AV_PIX_FMT_YUV422P },
			  { AV_PIX_FMT_YUV440P, AV_PIX_FMT_YUV420P } },
			{ { AV_PIX_FMT_YUV444P10, AV_PIX_FMT_YUV422P10 },
			  { AV_PIX_FMT_YUV440P10, AV_PIX_FMT_YUV420P10 } },
			{ { AV_PIX_FMT_YUV444P12, AV_PIX_FMT_YUV422P12 },
			  { AV_PIX_FMT_YUV440P12, AV_PIX_FMT_YUV420P12 } }
		};
		s->color_range = get_bits1(&s->gb) ? AVCOL_RANGE_JPEG : AVCOL_RANGE_MPEG;
		if (s->profile & 1) {
			s->ss_h = get_bits1(&s->gb);
			s->ss_v = get_bits1(&s->gb);
			s->pix_fmt = pix_fmt_for_ss[bits][s->ss_v][s->ss_h];
			if (s->pix_fmt == AV_PIX_FMT_YUV420P) {
				fprintf(stderr, "YUV 4:2:0 not supported in profile %d\n",
					s->profile);
				return AVERROR_INVALIDDATA;
			} else if (get_bits1(&s->gb)) {
				fprintf(stderr,
					"Profile %d color details reserved bit set\n",
					s->profile);
				return AVERROR_INVALIDDATA;
			}
		} else {
			s->ss_h = s->ss_v = 1;
			s->pix_fmt = pix_fmt_for_ss[bits][1][1];
		}
	}
	return 0;
}

static void vp9_print_uncompressed_header(VP9Context *s)
{
	int i;

	vp9_field("profile", s->profile);
	vp9_field("frame_width", s->w);
	vp9_field("frame_height", s->h);
	vp9_field("show_existing_frame", s->s.h.show_existing_frame);
	if (s->s.h.show_existing_frame)
		vp9_field("show_existing_idx", s->s.h.show_ref_idx);

	vp9_field("frame_type", !s->s.h.keyframe);
	vp9_field("show_frame", !s->s.h.invisible);
	vp9_field("error_resilient_mode", s->s.h.errorres);
	vp9_field("refresh_frame_context", s->s.h.refreshctx);
	vp9_field("frame_parallel_decoding_mode", s->s.h.parallelmode);
	vp9_field("frame_context_idx", s->s.h.framectxid);
	if (s->s.h.keyframe) {
		;
	}
	else {
		vp9_field("intra_only", s->s.h.intraonly);
		vp9_field("reset_frame_context", s->s.h.resetctx);
		vp9_field("refresh_frame_flags", s->s.h.refreshrefmask);
		for (i = 0; i < VP9_REFS_PER_FRAME; i++) {
			vp9_field("ref_frame_idx[%d]", i, s->s.h.refidx[i]);
			vp9_field("ref_frame_sign_bias[%d]", i, s->s.h.signbias[i]);
		}
		vp9_field("allow_high_precision_mv", s->s.h.highprecisionmvs);
		vp9_field("mcomp_filter_type", s->s.h.filtermode);
	}

	vp9_field("loop_filter_level", s->s.h.filter.level);
	vp9_field("loop_filter_sharpness", s->s.h.filter.sharpness);
	vp9_field("loop_filter_delta_enabled", s->s.h.lf_delta.enabled);
	if (s->s.h.lf_delta.enabled) {
		vp9_field("loop_filter_delta_update", s->s.h.lf_delta.updated);
		if (s->s.h.lf_delta.updated) {
			for (i = 0; i < 4; i++) {
				if (s->s.h.lf_delta.update_ref[i])
					vp9_field("loop_filter_ref_deltas[%d]", i, s->s.h.lf_delta.ref[i]);
			}
			for (i = 0; i < 2; i++) {
				if (s->s.h.lf_delta.update_mode[i])
					vp9_field("loop_filter_mode_deltas[%d]", i, s->s.h.lf_delta.mode[i]);
			}
		}
	}

	vp9_field("base_q_idx", s->s.h.yac_qi);
	vp9_field("delta_q_y_dc", s->s.h.ydc_qdelta);
	vp9_field("delta_q_uv_dc", s->s.h.uvdc_qdelta);
	vp9_field("delta_q_uv_ac", s->s.h.uvac_qdelta);

	vp9_field("segmentation_enabled", s->s.h.segmentation.enabled);

	vp9_field("tile_cols", s->s.h.tiling.tile_cols);
	vp9_field("tile_rows", s->s.h.tiling.tile_rows);
	vp9_field("compressed_header_size", s->s.h.compressed_header_size); // header_size_in_bytes
	vp9_field("uncompressed_header_size", s->s.h.uncompressed_header_size);
}

int vp9_decode_uncompressed_header(VP9Context *s, const uint8_t *data, size_t size)
{
	int c, i, j, w, h, max, ret, flag, sharp;
	int last_invisible;

	bs_init(&s->gb, (uint8_t *)data, size);
	uint64_t start_pos = (uint64_t)(void *)s->gb.p;
	if (get_bits(&s->gb, 2) != 0x2) { // frame marker
		fprintf(stderr, "invalid frame marker\n");
		return AVERROR_INVALIDDATA;
	}

	s->profile  = get_bits1(&s->gb);
	s->profile |= get_bits1(&s->gb) << 1;
	if (s->profile == 3)
		s->profile += get_bits1(&s->gb);
	if (s->profile > 3) {
		fprintf(stderr, "profile %d is not yet supported\n", s->profile);
		return AVERROR_INVALIDDATA;
	}
	s->s.h.profile = s->profile;

	s->s.h.show_existing_frame = get_bits1(&s->gb);
	if (s->s.h.show_existing_frame) {
		s->s.h.show_ref_idx = get_bits(&s->gb, 3);
		return 0;
	}

	s->last_keyframe  = s->s.h.keyframe;
	s->s.h.keyframe   = !get_bits1(&s->gb);

	last_invisible    = s->s.h.invisible;
	s->s.h.invisible  = !get_bits1(&s->gb);
	s->s.h.errorres   = get_bits1(&s->gb);
	s->s.h.use_last_frame_mvs = !s->s.h.errorres && !last_invisible;

	if (s->s.h.keyframe) {
		if (get_bits(&s->gb, 24) != VP9_SYNCCODE) { // synccode
			fprintf(stderr, "Invalid sync code\n");
			return AVERROR_INVALIDDATA;
		}
		if ((ret = vp9_read_colorspace_details(s)) < 0)
			return ret;
		// for profile 1, here follows the subsampling bits
		s->s.h.refreshrefmask = 0xff;
		w = get_bits(&s->gb, 16) + 1;
		h = get_bits(&s->gb, 16) + 1;
		if (get_bits1(&s->gb)) // display size
			skip_bits(&s->gb, 32);
	} else {
		s->s.h.intraonly = s->s.h.invisible ? get_bits1(&s->gb) : 0;
		s->s.h.resetctx  = s->s.h.errorres ? 0 : get_bits(&s->gb, 2);
		if (s->s.h.intraonly) {
			if (get_bits(&s->gb, 24) != VP9_SYNCCODE) { // synccode
				fprintf(stderr, "Invalid sync code\n");
				return AVERROR_INVALIDDATA;
			}
			if (s->profile >= 1) {
				if ((ret = vp9_read_colorspace_details(s)) < 0)
					return ret;
			} else {
				s->ss_h = s->ss_v = 1;
				s->s.h.bpp = 8;
				s->bpp_index = 0;
				s->bytesperpixel = 1;
				s->pix_fmt = AV_PIX_FMT_YUV420P;
				s->colorspace = AVCOL_SPC_BT470BG;
				s->color_range = AVCOL_RANGE_MPEG;
			}
			s->s.h.refreshrefmask = get_bits(&s->gb, 8);
			w = get_bits(&s->gb, 16) + 1;
			h = get_bits(&s->gb, 16) + 1;
			if (get_bits1(&s->gb)) /* render_and_frame_size_different */ 
				skip_bits(&s->gb, 32);
		} else {
			s->s.h.refreshrefmask = get_bits(&s->gb, 8);
			s->s.h.refidx[0]      = get_bits(&s->gb, 3);
			s->s.h.signbias[0]    = get_bits1(&s->gb) && !s->s.h.errorres;
			s->s.h.refidx[1]      = get_bits(&s->gb, 3);
			s->s.h.signbias[1]    = get_bits1(&s->gb) && !s->s.h.errorres;
			s->s.h.refidx[2]      = get_bits(&s->gb, 3);
			s->s.h.signbias[2]    = get_bits1(&s->gb) && !s->s.h.errorres;

			if (!s->s.refs[s->s.h.refidx[0]].buf[0] ||
			    !s->s.refs[s->s.h.refidx[1]].buf[0] ||
			    !s->s.refs[s->s.h.refidx[2]].buf[0]) {
				fprintf(stderr,
				       "Not all references are available\n");
				return AVERROR_INVALIDDATA;
			}

			if (get_bits1(&s->gb)) {
				w = s->s.refs[s->s.h.refidx[0]].width;
				h = s->s.refs[s->s.h.refidx[0]].height;
			} else if (get_bits1(&s->gb)) {
				w = s->s.refs[s->s.h.refidx[1]].width;
				h = s->s.refs[s->s.h.refidx[1]].height;
			} else if (get_bits1(&s->gb)) {
				w = s->s.refs[s->s.h.refidx[2]].width;
				h = s->s.refs[s->s.h.refidx[2]].height;
			} else {
				w = get_bits(&s->gb, 16) + 1;
				h = get_bits(&s->gb, 16) + 1;
			}
			// Note that in this code, "CUR_FRAME" is actually before we
			// have formally allocated a frame, and thus actually represents
			// the _last_ frame
			s->s.h.use_last_frame_mvs &=
				s->s.frames[CUR_FRAME].tf.width == w &&
				s->s.frames[CUR_FRAME].tf.height == h;
			if (get_bits1(&s->gb)) // display size
				skip_bits(&s->gb, 32);
			s->s.h.highprecisionmvs = get_bits1(&s->gb);
			s->s.h.filtermode = get_bits1(&s->gb) ? FILTER_SWITCHABLE :
							    get_bits(&s->gb, 2);
			s->s.h.allowcompinter = s->s.h.signbias[0] != s->s.h.signbias[1] ||
						s->s.h.signbias[0] != s->s.h.signbias[2];
			if (s->s.h.allowcompinter) {
				if (s->s.h.signbias[0] == s->s.h.signbias[1]) {
					s->s.h.fixcompref    = 2;
					s->s.h.varcompref[0] = 0;
					s->s.h.varcompref[1] = 1;
				} else if (s->s.h.signbias[0] == s->s.h.signbias[2]) {
					s->s.h.fixcompref    = 1;
					s->s.h.varcompref[0] = 0;
					s->s.h.varcompref[1] = 2;
				} else {
					s->s.h.fixcompref    = 0;
					s->s.h.varcompref[0] = 1;
					s->s.h.varcompref[1] = 2;
				}
			}
		}
	}

	flag = 1;
	for (i = 0; i < VP9_REF_FRAMES; i++) {
		if (s->s.h.refreshrefmask & flag) {
			s->s.refs[i].width = w;
			s->s.refs[i].height = h;
			s->s.refs[i].buf[0] = (void *)1;
		}
		flag <<= 1;
	}
	s->w = w;
	s->h = h;

	s->s.h.refreshctx   = s->s.h.errorres ? 0 : get_bits1(&s->gb);
	s->s.h.parallelmode = s->s.h.errorres ? 1 : get_bits1(&s->gb);
	s->s.h.framectxid   = c = get_bits(&s->gb, 2);
	if (s->s.h.keyframe || s->s.h.intraonly)
		s->s.h.framectxid = 0; // BUG: libvpx ignores this field in keyframes

	/* loopfilter header data */
	if (s->s.h.keyframe || s->s.h.errorres || s->s.h.intraonly) {
		// reset loopfilter defaults
		s->s.h.lf_delta.ref[0] = 1;
		s->s.h.lf_delta.ref[1] = 0;
		s->s.h.lf_delta.ref[2] = -1;
		s->s.h.lf_delta.ref[3] = -1;
		s->s.h.lf_delta.mode[0] = 0;
		s->s.h.lf_delta.mode[1] = 0;
		memset(s->s.h.segmentation.feat, 0, sizeof(s->s.h.segmentation.feat));
	}
	s->s.h.filter.level = get_bits(&s->gb, 6);
	sharp = get_bits(&s->gb, 3);
	// if sharpness changed, reinit lim/mblim LUTs. if it didn't change, keep
	// the old cache values since they are still valid
	if (s->s.h.filter.sharpness != sharp) {
		for (i = 1; i <= 63; i++) {
			int limit = i;

			if (sharp > 0) {
				limit >>= (sharp + 3) >> 2;
				limit = FFMIN(limit, 9 - sharp);
			}
			limit = FFMAX(limit, 1);

			s->filter_lut.lim_lut[i] = limit;
			s->filter_lut.mblim_lut[i] = 2 * (i + 2) + limit;
		}
	}
	s->s.h.filter.sharpness = sharp;
	if ((s->s.h.lf_delta.enabled = get_bits1(&s->gb))) {
		if ((s->s.h.lf_delta.updated = get_bits1(&s->gb))) {
			for (i = 0; i < 4; i++) {
				s->s.h.lf_delta.update_ref[i] = get_bits1(&s->gb);
				if (s->s.h.lf_delta.update_ref[i])
					s->s.h.lf_delta.ref[i] = get_sbits_inv(&s->gb, 6);
			}
			for (i = 0; i < 2; i++) {
				s->s.h.lf_delta.update_mode[i] = get_bits1(&s->gb);
				if (s->s.h.lf_delta.update_mode[i])
					s->s.h.lf_delta.mode[i] = get_sbits_inv(&s->gb, 6);
			}
		}
	}

	/* quantization header data */
	s->s.h.yac_qi      = get_bits(&s->gb, 8);
	s->s.h.ydc_qdelta  = get_bits1(&s->gb) ? get_sbits_inv(&s->gb, 4) : 0;
	s->s.h.uvdc_qdelta = get_bits1(&s->gb) ? get_sbits_inv(&s->gb, 4) : 0;
	s->s.h.uvac_qdelta = get_bits1(&s->gb) ? get_sbits_inv(&s->gb, 4) : 0;
	s->s.h.lossless    = s->s.h.yac_qi == 0 && s->s.h.ydc_qdelta == 0 &&
			   s->s.h.uvdc_qdelta == 0 && s->s.h.uvac_qdelta == 0;
	if (s->s.h.lossless)
		s->properties |= FF_CODEC_PROPERTY_LOSSLESS;

	/* segmentation header info */
	if ((s->s.h.segmentation.enabled = get_bits1(&s->gb))) {
		if ((s->s.h.segmentation.update_map = get_bits1(&s->gb))) {
			for (i = 0; i < 7; i++)
				s->s.h.segmentation.prob[i] =
					get_bits1(&s->gb) ? get_bits(&s->gb, 8) : 255;
			if ((s->s.h.segmentation.temporal = get_bits1(&s->gb)))
				for (i = 0; i < 3; i++)
					s->s.h.segmentation.pred_prob[i] =
						get_bits1(&s->gb) ? get_bits(&s->gb, 8) : 255;
		}

		if (get_bits1(&s->gb)) {
			s->s.h.segmentation.absolute_vals = get_bits1(&s->gb);
			for (i = 0; i < 8; i++) {
				if ((s->s.h.segmentation.feat[i].q_enabled = get_bits1(&s->gb)))
					 s->s.h.segmentation.feat[i].q_val = get_sbits_inv(&s->gb, 8);
				if ((s->s.h.segmentation.feat[i].lf_enabled = get_bits1(&s->gb)))
					 s->s.h.segmentation.feat[i].lf_val = get_sbits_inv(&s->gb, 6);
				if ((s->s.h.segmentation.feat[i].ref_enabled = get_bits1(&s->gb)))
					 s->s.h.segmentation.feat[i].ref_val = get_bits(&s->gb, 2);
				s->s.h.segmentation.feat[i].skip_enabled = get_bits1(&s->gb);
			}
		}
	}

	// set qmul[] based on Y/UV, AC/DC and segmentation Q idx deltas
	for (i = 0; i < (s->s.h.segmentation.enabled ? 8 : 1); i++) {
		int qyac, qydc, quvac, quvdc, lflvl, sh;

		if (s->s.h.segmentation.enabled &&
		    s->s.h.segmentation.feat[i].q_enabled) {
			if (s->s.h.segmentation.absolute_vals)
				qyac = av_clip_uintp2(s->s.h.segmentation.feat[i].q_val, 8);
			else
				qyac = av_clip_uintp2(s->s.h.yac_qi + s->s.h.segmentation.feat[i].q_val, 8);
		} else {
			qyac = s->s.h.yac_qi;
		}
		qydc  = av_clip_uintp2(qyac + s->s.h.ydc_qdelta, 8);
		quvdc = av_clip_uintp2(qyac + s->s.h.uvdc_qdelta, 8);
		quvac = av_clip_uintp2(qyac + s->s.h.uvac_qdelta, 8);
		qyac  = av_clip_uintp2(qyac, 8);

		s->s.h.segmentation.feat[i].qmul[0][0] = ff_vp9_dc_qlookup[s->bpp_index][qydc];
		s->s.h.segmentation.feat[i].qmul[0][1] = ff_vp9_ac_qlookup[s->bpp_index][qyac];
		s->s.h.segmentation.feat[i].qmul[1][0] = ff_vp9_dc_qlookup[s->bpp_index][quvdc];
		s->s.h.segmentation.feat[i].qmul[1][1] = ff_vp9_ac_qlookup[s->bpp_index][quvac];

		sh = s->s.h.filter.level >= 32;
		if (s->s.h.segmentation.enabled &&
		    s->s.h.segmentation.feat[i].lf_enabled) {
			if (s->s.h.segmentation.absolute_vals)
				lflvl = av_clip_uintp2(s->s.h.segmentation.feat[i].lf_val, 6);
			else
				lflvl = av_clip_uintp2(s->s.h.filter.level + s->s.h.segmentation.feat[i].lf_val, 6);
		} else {
			lflvl = s->s.h.filter.level;
		}
		if (s->s.h.lf_delta.enabled) {
			s->s.h.segmentation.feat[i].lflvl[0][0] =
				s->s.h.segmentation.feat[i].lflvl[0][1] =
					av_clip_uintp2(lflvl + (s->s.h.lf_delta.ref[0] * (1 << sh)), 6);
			for (j = 1; j < 4; j++) {
				s->s.h.segmentation.feat[i].lflvl[j][0] =
					av_clip_uintp2(lflvl + ((s->s.h.lf_delta.ref[j] +
						  s->s.h.lf_delta.mode[0]) * (1 << sh)), 6);
				s->s.h.segmentation.feat[i].lflvl[j][1] =
					av_clip_uintp2(lflvl + ((s->s.h.lf_delta.ref[j] +
						  s->s.h.lf_delta.mode[1]) * (1 << sh)), 6);
			}
		} else {
			memset(s->s.h.segmentation.feat[i].lflvl, lflvl,
			       sizeof(s->s.h.segmentation.feat[i].lflvl));
		}
	}

	for (s->s.h.tiling.log2_tile_cols = 0;
	     s->sb_cols > (64 << s->s.h.tiling.log2_tile_cols);
	     s->s.h.tiling.log2_tile_cols++) ;
	for (max = 0; (s->sb_cols >> max) >= 4; max++) ;
	max = FFMAX(0, max - 1);
	while (max > s->s.h.tiling.log2_tile_cols) {
		if (get_bits1(&s->gb))
			s->s.h.tiling.log2_tile_cols++;
		else
			break;
	}
	s->s.h.tiling.log2_tile_rows = decode012(&s->gb);
	s->s.h.tiling.tile_cols = 1 << s->s.h.tiling.log2_tile_cols;
	s->s.h.tiling.tile_rows = 1 << s->s.h.tiling.log2_tile_rows;

	// next 16 bits is size of the rest of the header (arith-coded)
	s->s.h.compressed_header_size = get_bits(&s->gb, 16);
	trailing_bits(&s->gb);
	s->s.h.uncompressed_header_size = (uint64_t)(void *)(s->gb.p) - start_pos;

	return 0;
}

void vp9_print_header(VP9Context *s)
{
	printf("{\n");
	vp9_print_uncompressed_header(s);
	printf("}\n");
}
