/*
 * Copyright 2023 Eileen Yoon <eyn@gmx.com>
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

#ifndef __VP9_DEC_H__
#define __VP9_DEC_H__

#include "bs.h"
#include "vpx_rac.h"

#include "libavutil/pixdesc.h"
#include "libavcodec/avcodec.h"

#define VP9_REFS_PER_FRAME     3
#define VP9_MAX_REF_FRAMES     4
#define VP9_NUM_REF_FRAMES     8
#define VP9_MIN_TILE_WIDTH_B64 4
#define VP9_MAX_TILE_WIDTH_B64 64

// Only need this for fixed-size arrays, for structs just assign.
#define vp9_copy(dest, src)              \
  do {                                   \
    assert(sizeof(dest) == sizeof(src)); \
    memcpy(dest, src, sizeof(src));      \
  } while (0)

#define vp9_zero(dest) memset(&(dest), 0, sizeof(dest))
#define vp9_zero_array(dest, n) memset(dest, 0, (n) * sizeof(*(dest)))

// block transform size
typedef uint8_t TX_SIZE;
#define TX_4X4 ((TX_SIZE)0)    // 4x4 transform
#define TX_8X8 ((TX_SIZE)1)    // 8x8 transform
#define TX_16X16 ((TX_SIZE)2)  // 16x16 transform
#define TX_32X32 ((TX_SIZE)3)  // 32x32 transform
#define TX_SIZES ((TX_SIZE)4)

// frame transform mode
typedef enum {
    ONLY_4X4 = 0,        // only 4x4 transform used
    ALLOW_8X8 = 1,       // allow block transform size up to 8x8
    ALLOW_16X16 = 2,     // allow block transform size up to 16x16
    ALLOW_32X32 = 3,     // allow block transform size up to 32x32
    TX_MODE_SELECT = 4,  // transform specified for each block
    TX_MODES = 5,
} TX_MODE;
#define TX_SWITCHABLE 4

typedef enum {
    DCT_DCT = 0,    // DCT  in both horizontal and vertical
    ADST_DCT = 1,   // ADST in vertical, DCT in horizontal
    DCT_ADST = 2,   // DCT  in vertical, ADST in horizontal
    ADST_ADST = 3,  // ADST in both directions
    TX_TYPES = 4
} TX_TYPE;

typedef enum {
    VP9_LAST_FLAG = 1 << 0,
    VP9_GOLD_FLAG = 1 << 1,
    VP9_ALT_FLAG = 1 << 2,
} VP9_REFFRAME;

enum FilterMode {
    FILTER_8TAP_SMOOTH,
    FILTER_8TAP_REGULAR,
    FILTER_8TAP_SHARP,
    FILTER_BILINEAR,
    N_FILTERS,
    FILTER_SWITCHABLE = N_FILTERS,
};

enum InterPredMode {
    NEARESTMV = 10,
    NEARMV    = 11,
    ZEROMV    = 12,
    NEWMV     = 13,
};

enum CompPredMode {
    PRED_SINGLEREF,
    PRED_COMPREF,
    PRED_SWITCHABLE,
};

#if 0
#define AVERROR_INVALIDDATA -1
#endif

typedef struct ThreadFrame {
    int width;
    int height;
    int rows;
    int cols;
    int subsampling_x;
    int subsampling_y;
    int bit_depth;
    int key_frame;
} ThreadFrame;

typedef struct VP9Frame {
    ThreadFrame tf;
    uint8_t *segmentation_map;
    int uses_2pass;
} VP9Frame;

/* bitstream header */
typedef struct VP9BitstreamHeader {
    uint8_t profile;
    uint8_t bpp;
    uint8_t keyframe;
    uint8_t show_existing_frame;
    uint8_t show_ref_idx;
    uint8_t invisible;
    uint8_t errorres;
    uint8_t intraonly;
    uint8_t resetctx;
    uint8_t refreshrefmask;
    uint8_t highprecisionmvs;
    enum FilterMode filtermode;
    uint8_t allowcompinter;
    uint8_t refreshctx;
    uint8_t parallelmode;
    uint8_t framectxid;
    uint8_t use_last_frame_mvs;
    uint8_t refidx[3];
    uint8_t signbias[3];
    uint8_t fixcompref;
    uint8_t varcompref[2];
    struct {
        uint8_t level;
        int8_t sharpness;
    } filter;
    struct {
        uint8_t enabled;
        uint8_t updated;
        int8_t update_ref[4];
        int8_t ref[4];
        int8_t update_mode[2];
        int8_t mode[2];
    } lf_delta;
    uint8_t yac_qi;
    int8_t ydc_qdelta, uvdc_qdelta, uvac_qdelta;
    uint8_t lossless;
#define MAX_SEGMENT 8
    struct {
        uint8_t enabled;
        uint8_t temporal;
        uint8_t absolute_vals;
        uint8_t update_map;
        uint8_t prob[7];
        uint8_t pred_prob[3];
        struct {
            uint8_t q_enabled;
            uint8_t lf_enabled;
            uint8_t ref_enabled;
            uint8_t skip_enabled;
            uint8_t ref_val;
            int16_t q_val;
            int8_t lf_val;
            int16_t qmul[2][2];
            uint8_t lflvl[4][2];
        } feat[MAX_SEGMENT];
    } segmentation;
    TX_MODE txfmmode;
    enum CompPredMode comppredmode;
    struct {
        unsigned log2_tile_cols, log2_tile_rows;
    } tiling;

    int uncompressed_header_size;
    int compressed_header_size;
} VP9BitstreamHeader;

typedef struct VP9SharedContext {
    VP9BitstreamHeader h;
    ThreadFrame refs[8];
#define CUR_FRAME	 0
#define REF_FRAME_MVPAIR 1
#define REF_FRAME_SEGMAP 2
    VP9Frame frames[3];
} VP9SharedContext;

typedef struct VP9Filter {
    uint8_t level[8 * 8];
    uint8_t /* bit=col */ mask[2 /* 0=y, 1=uv */][2 /* 0=col, 1=row */]
                              [8 /* rows */][4 /* 0=16, 1=8, 2=4, 3=inner4 */];
} VP9Filter;

typedef uint8_t vp9_coeff_probs_model[2][6][6][3];
typedef unsigned int vp9_coeff_count_model[2][6][6][4];

#define PLANE_TYPES 2
#define REF_TYPES 2  // intra=0, inter=1
#define COEF_BANDS 6
#define UNCONSTRAINED_NODES 3
#define COEFF_CONTEXTS 6
#define BAND_COEFF_CONTEXTS(band) ((band) == 0 ? 3 : COEFF_CONTEXTS)

/* Symbols for coding magnitude class of nonzero components */
#define MV_CLASSES 11
#define CLASS0_BITS 1 /* bits at integer precision for class 0 */
#define CLASS0_SIZE (1 << CLASS0_BITS)
#define MV_OFFSET_BITS (MV_CLASSES + CLASS0_BITS - 2)
#define MV_FP_SIZE 4

#define MV_MAX_BITS (MV_CLASSES + CLASS0_BITS + 2)
#define MV_MAX ((1 << MV_MAX_BITS) - 1)
#define MV_VALS ((MV_MAX << 1) + 1)

#define MV_IN_USE_BITS 14
#define MV_UPP ((1 << MV_IN_USE_BITS) - 1)
#define MV_LOW (-(1 << MV_IN_USE_BITS))

typedef struct nmv_component_counts {
    unsigned int sign[2];
    unsigned int classes[MV_CLASSES];
    unsigned int class0[CLASS0_SIZE];
    unsigned int bits[MV_OFFSET_BITS][2];
    unsigned int class0_fp[CLASS0_SIZE][MV_FP_SIZE];
    unsigned int fp[MV_FP_SIZE];
    unsigned int class0_hp[2];
    unsigned int hp[2];
} nmv_component_counts;

typedef struct nmv_context_counts {
    unsigned int joints[4];
    nmv_component_counts comps[2];
} nmv_context_counts;

struct tx_counts {
    unsigned int p32x32[2][4];
    unsigned int p16x16[2][3];
    unsigned int p8x8[2][2];
    unsigned int tx_totals[4];
};

struct __attribute__((packed, scalar_storage_order("little-endian"))) tx_probs {
    uint8_t p32x32[2][3];
    uint8_t p16x16[2][2];
    uint8_t p8x8[2][1];
};

typedef struct __attribute__((packed, scalar_storage_order("little-endian"))) nmv_component {
    uint8_t sign;
    uint8_t classes[MV_CLASSES - 1];
    uint8_t class0[CLASS0_SIZE - 1];
    uint8_t bits[MV_OFFSET_BITS];
    uint8_t class0_fp[CLASS0_SIZE][MV_FP_SIZE - 1];
    uint8_t fp[MV_FP_SIZE - 1];
    uint8_t class0_hp;
    uint8_t hp;
} nmv_component;

typedef struct __attribute__((packed, scalar_storage_order("little-endian"))) nmv_context {
    uint8_t joints[3];
    nmv_component comps[2];
} nmv_context;

typedef struct __attribute__((packed, scalar_storage_order("little-endian"))) VP9ProbContext {
    uint8_t y_mode[4][9];
    uint8_t uv_mode[10][9];
    uint8_t partition[16][3];
    uint8_t switchable_interp[4][2];
    uint8_t inter_mode[7][3];
    uint8_t intra_inter[4];
    uint8_t comp_inter[5];
    uint8_t single_ref[5][2];
    uint8_t comp_ref[5];
    struct tx_probs tx;
    uint8_t skip[3];
    nmv_context nmvc;
    uint8_t coef[4][2][2][6][6][3];
} VP9ProbContext;

typedef struct VP9FrameCounts {
    unsigned int y_mode[4][10];
    unsigned int uv_mode[10][10];
    unsigned int partition[16][4];
    unsigned int coef[4][2][2][6][6][4];
    unsigned int eob_branch[4][2][2][6][6];
    unsigned int switchable_interp[4][3];
    unsigned int inter_mode[7][4];
    unsigned int intra_inter[4][2];
    unsigned int comp_inter[5][2];
    unsigned int single_ref[5][2][2];
    unsigned int comp_ref[5][2];
    struct tx_counts tx;
    unsigned int skip[3][2];
    nmv_context_counts mv;
} VP9FrameCounts;

typedef struct VP9Context {
    VP9SharedContext s;
    struct bitstream gb;
    VPXRangeCoder c;
    VP9FrameCounts counts;

    int profile;
    unsigned properties;
    int pass, active_tile_cols;

    uint32_t w, h;
    uint8_t bd;
    uint8_t sx, sy;
    uint8_t last_bpp, bpp_index, bytesperpixel;
    uint8_t last_keyframe;
    // sb_cols/rows, rows/cols and last_fmt are used for allocating all internal
    // arrays, and are thus per-thread. w/h and gf_fmt are synced between threads
    // and are therefore per-stream. pix_fmt represents the value in the header
    // of the currently processed frame.
    enum AVPixelFormat pix_fmt, last_fmt, gf_fmt;
    enum AVColorSpace colorspace;
    enum AVPixelFormat color_range;
    uint32_t sb_cols, sb_rows, rows, cols;
    ThreadFrame next_refs[8];

    struct {
        uint8_t lim_lut[64];
        uint8_t mblim_lut[64];
    } filter_lut;

    struct {
        VP9ProbContext p;
    } prob_ctx[4];
    struct {
        VP9ProbContext p;
    } prob;

    // contextual (above) cache
    uint8_t *above_partition_ctx;
    uint8_t *above_mode_ctx;
    // FIXME maybe merge some of the below in a flags field?
    uint8_t *above_y_nnz_ctx;
    uint8_t *above_uv_nnz_ctx[2];
    uint8_t *above_skip_ctx; // 1bit
    uint8_t *above_txfm_ctx; // 2bit
    uint8_t *above_segpred_ctx; // 1bit
    uint8_t *above_intra_ctx; // 1bit
    uint8_t *above_comp_ctx; // 1bit
    uint8_t *above_ref_ctx; // 2bit
    uint8_t *above_filter_ctx;

    // whole-frame cache
    uint8_t *intra_pred_data[3];
    VP9Filter *lflvl;

    // block reconstruction intermediates
    int block_alloc_using_2pass;
    uint16_t mvscale[3][2];
    uint8_t mvstep[3][2];
} VP9Context;

#endif /* __VP9_DEC_H__ */
