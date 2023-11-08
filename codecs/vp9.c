/*
 * Copyright 2023 Eileen Yoon <eyn@gmx.com>
 *
 * Based on libavcodec, libvpx
 *
 * All Rights Reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice (including the next
 * paragraph) shall be included in all copies or substantial portions of the
 * Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>

#include "bs.h"
#include "vp9_dec.h"
#include "vp9_data.h"
#include "vp9_probs.h"
#include "vp9.h"
#include "vpx_rac.h"
#include "vpx_dsp_common.h"
#include "util.h"

#define vp9_log(a, ...)   printf("[VP9] " a, ##__VA_ARGS__)
#define vp9_field(a, ...) printf("\t" a " = %d\n", ##__VA_ARGS__)

#define VP9_SYNCCODE	    0x498342

// The sign bit is at the end, not the start, of a bit sequence
static inline int get_sbits_inv(struct bitstream *gb, int n)
{
    int v = get_bits(gb, n);
    return get_bits1(gb) ? -v : v;
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
        s->sx = s->sy = 0;
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
            s->sx = get_bits1(&s->gb);
            s->sy = get_bits1(&s->gb);
            s->pix_fmt = pix_fmt_for_ss[bits][s->sy][s->sx];
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
            s->sx = s->sy = 1;
            s->pix_fmt = pix_fmt_for_ss[bits][1][1];
        }
    }
    return 0;
}

static void vp9_init_mode_probs(VP9Context *s) {
    VP9ProbContext *p = &s->prob.p;
    vp9_copy(p->uv_mode, vp9_default_if_uv_probs);
    vp9_copy(p->y_mode, vp9_default_if_y_probs);
    vp9_copy(p->switchable_interp, default_switchable_interp_prob);
    vp9_copy(p->partition, vp9_default_partition_probs);
    vp9_copy(p->intra_inter, default_intra_inter_p);
    vp9_copy(p->comp_inter, default_comp_inter_p);
    vp9_copy(p->comp_ref, default_comp_ref_p);
    vp9_copy(p->single_ref, default_single_ref_p);
    p->tx = default_tx_probs;
    vp9_copy(p->skip, default_skip_probs);
    vp9_copy(p->inter_mode, default_inter_mode_probs);
}

static void vp9_setup_past_independence(VP9Context *s)
{
    VP9ProbContext *p = &s->prob.p;
    int i;

    // reset loopfilter defaults
    s->s.h.filter.sharpness = -1;
    s->s.h.lf_delta.ref[0] = 1;
    s->s.h.lf_delta.ref[1] = 0;
    s->s.h.lf_delta.ref[2] = -1;
    s->s.h.lf_delta.ref[3] = -1;
    s->s.h.lf_delta.mode[0] = 0;
    s->s.h.lf_delta.mode[1] = 0;
    memset(s->s.h.segmentation.feat, 0, sizeof(s->s.h.segmentation.feat));
    memcpy(p->coef, ff_vp9_default_coef_probs, sizeof(ff_vp9_default_coef_probs));
    vp9_init_mode_probs(s);
    p->nmvc = default_nmv_context;

    if (s->s.h.keyframe || s->s.h.errorres || (s->s.h.intraonly && s->s.h.resetctx == 3)) {
        // Reset all frame contexts.
        for (i = 0; i < 4; ++i)
            s->prob_ctx[i].p = *p;
    } else if (s->s.h.resetctx == 2) {
        // Reset only the frame context specified in the frame header.
        s->prob_ctx[s->s.h.framectxid].p = *p;
    }
}

static void vp9_parse_frame_size(VP9Context *s)
{
    s->w = get_bits(&s->gb, 16) + 1;
    s->h = get_bits(&s->gb, 16) + 1;
    s->cols = (s->w + 7) >> 3;
    s->rows = (s->h + 7) >> 3;
    s->sb_cols = (s->cols + 7) >> 3;
    s->sb_rows = (s->rows + 7) >> 3;
}

static void vp9_parse_render_size(VP9Context *s)
{
    if (get_bits1(&s->gb)) { // render_and_frame_size_different
        get_bits(&s->gb, 16) + 1;
        get_bits(&s->gb, 16) + 1;
    }
}

static uint32_t vp9_read_increment(VP9Context *s, uint32_t rmin, uint32_t rmax)
{
    uint32_t v;
    for (v = rmin; v < rmax;) {
        if (s->gb.bits_left < 1) {
            fprintf(stderr, "Bitstream ended.\n");
            return AVERROR_INVALIDDATA;
        }
        if (get_bits1(&s->gb))
            ++v;
        else
            break;
    }
    return v;
}

int vp9_decode_uncompressed_header(VP9Context *s, const uint8_t *data, size_t size)
{
    int c, i, j, ret, sharp;
    int last_invisible;

    uint64_t start_pos = (uint64_t)(void *)data;
    bs_init(&s->gb, (uint8_t *)data, size);
    if (get_bits(&s->gb, 2) != 0x2) {
        fprintf(stderr, "Invalid frame marker\n");
        return AVERROR_INVALIDDATA;
    }

    s->profile  = get_bits1(&s->gb);
    s->profile |= get_bits1(&s->gb) << 1;
    if (s->profile == 3)
        s->profile += get_bits1(&s->gb);
    if (s->profile > 3) {
        fprintf(stderr, "Profile %d is not yet supported\n", s->profile);
        return AVERROR_INVALIDDATA;
    }
    s->s.h.profile = s->profile;

    s->s.h.show_existing_frame = get_bits1(&s->gb);
    if (s->s.h.show_existing_frame) {
        s->s.h.show_ref_idx = get_bits(&s->gb, 3);
        s->s.h.compressed_header_size = 0;
        s->s.h.filter.level = 0;
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
        vp9_parse_frame_size(s);
        vp9_parse_render_size(s);
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
                s->sx = s->sy = 1;
                s->s.h.bpp = 8;
                s->bpp_index = 0;
                s->bytesperpixel = 1;
                s->pix_fmt = AV_PIX_FMT_YUV420P;
                s->colorspace = AVCOL_SPC_BT470BG;
                s->color_range = AVCOL_RANGE_MPEG;
            }
            s->s.h.refreshrefmask = get_bits(&s->gb, 8);
            vp9_parse_frame_size(s);
            vp9_parse_render_size(s);
        } else {
            s->s.h.refreshrefmask = get_bits(&s->gb, 8);
            s->s.h.refidx[0]      = get_bits(&s->gb, 3);
            s->s.h.signbias[0]    = get_bits1(&s->gb) && !s->s.h.errorres;
            s->s.h.refidx[1]      = get_bits(&s->gb, 3);
            s->s.h.signbias[1]    = get_bits1(&s->gb) && !s->s.h.errorres;
            s->s.h.refidx[2]      = get_bits(&s->gb, 3);
            s->s.h.signbias[2]    = get_bits1(&s->gb) && !s->s.h.errorres;

            for (i = 0; i < VP9_REFS_PER_FRAME; i++) {
                if (get_bits1(&s->gb)) {
                    s->w = s->s.refs[s->s.h.refidx[i]].width;
                    s->h = s->s.refs[s->s.h.refidx[i]].height;
                    s->sx = s->s.refs[s->s.h.refidx[i]].subsampling_x;
                    s->sy = s->s.refs[s->s.h.refidx[i]].subsampling_y;
                    s->bd = s->s.refs[s->s.h.refidx[i]].bit_depth;
                    break;
                }
            }
            if (i >= VP9_REFS_PER_FRAME)
                vp9_parse_frame_size(s);
            else {
                s->cols = (s->w + 7) >> 3;
                s->rows = (s->h + 7) >> 3;
                s->sb_cols = (s->cols + 7) >> 3;
                s->sb_rows = (s->rows + 7) >> 3;
            }
            vp9_parse_render_size(s);

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

    s->s.h.refreshctx   = s->s.h.errorres ? 0 : get_bits1(&s->gb);
    s->s.h.parallelmode = s->s.h.errorres ? 1 : get_bits1(&s->gb);
    s->s.h.framectxid   = c = get_bits(&s->gb, 2);
    if (s->s.h.keyframe || s->s.h.intraonly)
        s->s.h.framectxid = 0; // BUG: libvpx ignores this field in keyframes

    if (!s->s.h.errorres && !s->s.h.parallelmode)
        vp9_zero(s->counts);

    if (s->s.h.keyframe || s->s.h.errorres || s->s.h.intraonly)
        vp9_setup_past_independence(s);

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

    uint8_t min_log2_tile_cols = 0;
    while ((VP9_MAX_TILE_WIDTH_B64 << min_log2_tile_cols) < s->sb_cols)
        ++min_log2_tile_cols;
    uint8_t max_log2_tile_cols = 0;
    while ((s->sb_cols >> (max_log2_tile_cols + 1)) >= VP9_MIN_TILE_WIDTH_B64)
        ++max_log2_tile_cols;
    s->s.h.tiling.log2_tile_cols = vp9_read_increment(s, min_log2_tile_cols, max_log2_tile_cols);
    s->s.h.tiling.log2_tile_rows = vp9_read_increment(s, 0, 2);

    // next 16 bits is size of the rest of the header (arith-coded)
    s->s.h.compressed_header_size = get_bits(&s->gb, 16);
    trailing_bits(&s->gb);
    s->s.h.uncompressed_header_size = (uint64_t)(void *)(s->gb.p) - start_pos;

    for (i = 0; i < VP9_NUM_REF_FRAMES; i++) {
        if (s->s.h.refreshrefmask & (1 << i)) {
            s->s.refs[s->s.h.refidx[i]].width = s->w;
            s->s.refs[s->s.h.refidx[i]].height = s->h;
            s->s.refs[s->s.h.refidx[i]].subsampling_x = s->sx;
            s->s.refs[s->s.h.refidx[i]].subsampling_y = s->sy;
            s->s.refs[s->s.h.refidx[i]].bit_depth = s->bd;
        }
    }

    return 0;
}

static int inv_recenter_nonneg(int v, int m)
{
    if (v > 2 * m) return v;
    return (v & 1) ? m - ((v + 1) >> 1) : m + (v >> 1);
}

static inline int decode_uniform(vpx_reader *r)
{
    const int l = 8;
    const int m = (1 << l) - 191;
    const int v = vpx_read_literal(r, l - 1);
    return v < m ? v : (v << 1) - m + vpx_read_bit(r);
}

static int decode_term_subexp(VPXRangeCoder *c)
{
    if (!vpx_read_bit(c)) return vpx_read_literal(c, 4);
    if (!vpx_read_bit(c)) return vpx_read_literal(c, 4) + 16;
    if (!vpx_read_bit(c)) return vpx_read_literal(c, 5) + 32;
    return decode_uniform(c) + 64;
}

static int inv_remap_prob(int v, int m)
{
    static const uint8_t inv_map_table[255] = {
          7,  20,  33,  46,  59,  72,  85,  98, 111, 124, 137, 150, 163, 176,
        189, 202, 215, 228, 241, 254,   1,   2,   3,   4,   5,   6,   8,   9,
         10,  11,  12,  13,  14,  15,  16,  17,  18,  19,  21,  22,  23,  24,
         25,  26,  27,  28,  29,  30,  31,  32,  34,  35,  36,  37,  38,  39,
         40,  41,  42,  43,  44,  45,  47,  48,  49,  50,  51,  52,  53,  54,
         55,  56,  57,  58,  60,  61,  62,  63,  64,  65,  66,  67,  68,  69,
         70,  71,  73,  74,  75,  76,  77,  78,  79,  80,  81,  82,  83,  84,
         86,  87,  88,  89,  90,  91,  92,  93,  94,  95,  96,  97,  99, 100,
        101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 112, 113, 114, 115,
        116, 117, 118, 119, 120, 121, 122, 123, 125, 126, 127, 128, 129, 130,
        131, 132, 133, 134, 135, 136, 138, 139, 140, 141, 142, 143, 144, 145,
        146, 147, 148, 149, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160,
        161, 162, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175,
        177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 190, 191,
        192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 203, 204, 205, 206,
        207, 208, 209, 210, 211, 212, 213, 214, 216, 217, 218, 219, 220, 221,
        222, 223, 224, 225, 226, 227, 229, 230, 231, 232, 233, 234, 235, 236,
        237, 238, 239, 240, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251,
        252, 253, 253,
    };
    int d;

    /* This code is trying to do a differential probability update. For a
     * current probability A in the range [1, 255], the difference to a new
     * probability of any value can be expressed differentially as 1-A, 255-A
     * where some part of this (absolute range) exists both in positive as
     * well as the negative part, whereas another part only exists in one
     * half. We're trying to code this shared part differentially, i.e.
     * times two where the value of the lowest bit specifies the sign, and
     * the single part is then coded on top of this. This absolute difference
     * then again has a value of [0, 254], but a bigger value in this range
     * indicates that we're further away from the original value A, so we
     * can code this as a VLC code, since higher values are increasingly
     * unlikely. The first 20 values in inv_map_table[] allow 'cheap, rough'
     * updates vs. the 'fine, exact' updates further down the range, which
     * adds one extra dimension to this differential update model. */

    assert(v < (int)(sizeof(inv_map_table) / sizeof(inv_map_table[0])));
    v = inv_map_table[v];
    m--;
    if ((m << 1) <= 255) {
        return 1 + inv_recenter_nonneg(v, m);
    } else {
        return 255 - inv_recenter_nonneg(v, 255 - 1 - m);
    }
}

static void vp9_diff_update_prob(VPXRangeCoder *c, uint8_t *p)
{
    if (vpx_read(c, 252)) {
        const int delp = decode_term_subexp(c);
        *p = (uint8_t)inv_remap_prob(delp, *p);
    }
}

static void vp9_update_mv_probs(VPXRangeCoder *c, uint8_t *p)
{
    if (vpx_read(c, 252))
        *p = (vpx_read_literal(c, 7) << 1) | 1;
}

int vp9_decode_compressed_header(VP9Context *s, const uint8_t *data, size_t size)
{
    int c, i, j, k, l, m, n, err;

    c = s->s.h.framectxid;
    VP9ProbContext *p = &s->prob.p;
    printf("sz: %d\n", size);

    data += s->s.h.uncompressed_header_size;
    err = vpx_reader_init(&s->c, data, size, NULL, NULL);
    if (err) {
        fprintf(stderr, "Marker bit was set\n");
        return AVERROR_INVALIDDATA;
    }

    s->prob.p = s->prob_ctx[c].p;

    // txfm updates
    if (s->s.h.lossless) {
        s->s.h.txfmmode = ONLY_4X4;
    } else {
        s->s.h.txfmmode = vpx_read_literal(&s->c, 2);
        if (s->s.h.txfmmode == ALLOW_32X32)
            s->s.h.txfmmode += vpx_read_bit(&s->c);

        if (s->s.h.txfmmode == TX_MODE_SELECT) {
            for (i = 0; i < 2; i++)
                vp9_diff_update_prob(&s->c, &p->tx.p8x8[i][0]);
            for (i = 0; i < 2; i++)
                for (j = 0; j < 2; j++)
                    vp9_diff_update_prob(&s->c, &p->tx.p16x16[i][j]);
            for (i = 0; i < 2; i++)
                for (j = 0; j < 3; j++)
                    vp9_diff_update_prob(&s->c, &p->tx.p32x32[i][j]);
        }
    }

    // coef updates
    for (i = 0; i < 4; i++) {
        uint8_t (*ref)[2][6][6][3] = p->coef[i];
        if (vpx_read_bit(&s->c)) {
            for (j = 0; j < 2; j++)
                for (k = 0; k < 2; k++)
                    for (l = 0; l < 6; l++)
                        for (m = 0; m < 6; m++) {
                            uint8_t *r = ref[j][k][l][m];
                            if (m >= 3 && l == 0) // dc only has 3 pt
                                break;
                            for (n = 0; n < 3; n++) {
                                vp9_diff_update_prob(&s->c, &r[n]);
                            }
                        }
        } else {
            for (j = 0; j < 2; j++)
                for (k = 0; k < 2; k++)
                    for (l = 0; l < 6; l++)
                        for (m = 0; m < 6; m++) {
                            uint8_t *q = p->coef[i][j][k][l][m];
                            uint8_t *r = ref[j][k][l][m];
                            if (m > 3 && l == 0) // dc only has 3 pt
                                break;
                            memcpy(q, r, 3);
                        }
        }
    }

    // mode updates
    for (i = 0; i < 3; ++i)
        vp9_diff_update_prob(&s->c, &p->skip[i]);

    if (!s->s.h.keyframe && !s->s.h.intraonly) {
        for (i = 0; i < 7; i++)
            for (j = 0; j < 3; j++)
                vp9_diff_update_prob(&s->c, &p->inter_mode[i][j]);

        if (s->s.h.filtermode == FILTER_SWITCHABLE)
            for (i = 0; i < 4; i++)
                for (j = 0; j < 2; j++)
                    vp9_diff_update_prob(&s->c, &p->switchable_interp[i][j]);

        for (i = 0; i < 4; i++)
            vp9_diff_update_prob(&s->c, &p->intra_inter[i]);

        if (s->s.h.allowcompinter) {
            s->s.h.comppredmode = vpx_read_bit(&s->c);
            if (s->s.h.comppredmode)
                s->s.h.comppredmode += vpx_read_bit(&s->c);
            if (s->s.h.comppredmode == PRED_SWITCHABLE)
                for (i = 0; i < 5; i++)
                    vp9_diff_update_prob(&s->c, &p->comp_inter[i]);
        } else {
            s->s.h.comppredmode = PRED_SINGLEREF;
        }

        if (s->s.h.comppredmode != PRED_COMPREF) {
            for (i = 0; i < 5; i++) {
                vp9_diff_update_prob(&s->c, &p->single_ref[i][0]);
                vp9_diff_update_prob(&s->c, &p->single_ref[i][1]);
            }
        }

        if (s->s.h.comppredmode != PRED_SINGLEREF) {
            for (i = 0; i < 5; i++)
                vp9_diff_update_prob(&s->c, &p->comp_ref[i]);
        }

        for (i = 0; i < 4; i++)
            for (j = 0; j < 9; j++)
                vp9_diff_update_prob(&s->c, &p->y_mode[i][j]);

        for (i = 0; i < 16; i++)
            for (j = 0; j < 3; j++)
                vp9_diff_update_prob(&s->c, &p->partition[i][j]);

        // mv fields don't use the update_prob subexp model for some reason
        for (i = 0; i < 3; i++)
            vp9_update_mv_probs(&s->c, &p->nmvc.joints[i]);

        for (i = 0; i < 2; i++) {
            vp9_update_mv_probs(&s->c, &p->nmvc.comps[i].sign);
            for (j = 0; j < 10; j++)
                vp9_update_mv_probs(&s->c, &p->nmvc.comps[i].classes[j]);
            vp9_update_mv_probs(&s->c, &p->nmvc.comps[i].class0[0]);
            for (j = 0; j < 10; j++)
                vp9_update_mv_probs(&s->c, &p->nmvc.comps[i].bits[j]);
        }

        for (i = 0; i < 2; i++) {
            for (j = 0; j < 2; j++)
                for (k = 0; k < 3; k++)
                    vp9_update_mv_probs(&s->c, &p->nmvc.comps[i].class0_fp[j][k]);

            for (j = 0; j < 3; j++)
                vp9_update_mv_probs(&s->c, &p->nmvc.comps[i].fp[j]);
        }

        if (s->s.h.highprecisionmvs) {
            for (i = 0; i < 2; i++) {
                vp9_update_mv_probs(&s->c, &p->nmvc.comps[i].class0_hp);
                vp9_update_mv_probs(&s->c, &p->nmvc.comps[i].hp);
            }
        }
    }

    if (s->s.h.refreshctx && s->s.h.parallelmode) {
        for (i = 0; i < 4; i++) {
            for (j = 0; j < 2; j++)
                for (k = 0; k < 2; k++)
                    for (l = 0; l < 6; l++)
                        for (m = 0; m < 6; m++)
                            memcpy(s->prob_ctx[s->s.h.framectxid].p.coef[i][j][k][l][m],
                                   s->prob.p.coef[i][j][k][l][m], 3);
            if (s->s.h.txfmmode == i)
                break;
        }
        s->prob_ctx[s->s.h.framectxid].p = s->prob.p;
    }

    /* Start of AVD-specific hacks, hopefully none more. Notice this comes _after_
     * updating the global context. Below is from libvpx/vp9/common/vp9_onyxc_int.h.

        static INLINE int frame_is_intra_only(const VP9_COMMON *const cm) {
          return cm->frame_type == KEY_FRAME || cm->intra_only;
        }

        static INLINE void set_partition_probs(const VP9_COMMON *const cm,
                                               MACROBLOCKD *const xd) {
          xd->partition_probs =
              frame_is_intra_only(cm)
                  ? &vp9_kf_partition_probs[0]
                  : (const vpx_prob(*)[PARTITION_TYPES - 1]) cm->fc->partition_prob;
        }

        static INLINE void vp9_init_macroblockd(VP9_COMMON *cm, MACROBLOCKD *xd,
                                                tran_low_t *dqcoeff) {
          int i;
          // some stuff
          set_partition_probs(cm, xd);
        }

     * Very confusingly 9.3.2. "Probability Selection Process" specifically states
     * !keyframe && intraonly frames use the kf probability tables (as opposed to
     * the default/if probs), but libavcodec and libvpx both check for (keyframe
     * || intraonly), so let's assume that.
     *
     * On keyframes, macOS loads the _kf_ partition table, as if it was decoding
     * the first macroblock. It's not a driver bug because the hardware faults
     * and requires hard-reboot if loaded the default table. And it's not "always
     * take kf in independence" either because it's not reflected in the global
     * context (that'd shift the adapted probs). Same for uv_mode.
     *
     * So is it "the probs instantaneously at the decoding the first macroblock"?
     * It is not because we do not load the kf variant of y_mode. That also faults.
     */
#if 1
    if (s->s.h.keyframe || s->s.h.intraonly) {
        vp9_copy(s->prob.p.partition, vp9_kf_partition_probs);
        vp9_copy(s->prob.p.uv_mode, vp9_kf_uv_mode_probs);
    }
#endif

    return 0;
}

static void vp9_print_uncompressed_header(VP9Context *s)
{
    int i;

    vp9_field("profile", s->profile);
    vp9_field("frame_width", s->w);
    vp9_field("frame_height", s->h);
    vp9_field("show_existing_frame", s->s.h.show_existing_frame);
    if (s->s.h.show_existing_frame) {
        vp9_field("frame_to_show_map_idx", s->s.h.show_ref_idx);
        vp9_field("header_size_in_bytes", s->s.h.compressed_header_size);
        return;
    }

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

    vp9_field("tile_cols_log2", s->s.h.tiling.log2_tile_cols);
    vp9_field("tile_rows_log2", s->s.h.tiling.log2_tile_rows);
    vp9_field("compressed_header_size", s->s.h.compressed_header_size); // header_size_in_bytes
    vp9_field("uncompressed_header_size", s->s.h.uncompressed_header_size);
}

void vp9_print_header(VP9Context *s)
{
    printf("{\n");
    vp9_print_uncompressed_header(s);
    printf("}\n");
    //printf("\tskip: [%d, %d, %d]\n", s->prob.p.skip[0], s->prob.p.skip[1], s->prob.p.skip[2]);
}

void vp9_save_probs(VP9Context *s, const char *path)
{
    write_to_file(path, (char *)&s->prob.p, sizeof(s->prob.p));
}
