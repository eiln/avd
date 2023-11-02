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

#ifndef __VP9_SHARED_H__
#define __VP9_SHARED_H__

#include "bs.h"

#include "libavutil/pixdesc.h"
#include "libavcodec/avcodec.h"

#define VP9_REFS_PER_FRAME     3
#define VP9_REF_FRAMES_LOG2    3
#define VP9_REF_FRAMES         (1 << VP9_REF_FRAMES_LOG2)
#define VP9_FRAME_CONTEXTS_LOG2 2

enum TxfmMode {
	TX_4X4,
	TX_8X8,
	TX_16X16,
	TX_32X32,
	N_TXFM_SIZES,
	TX_SWITCHABLE = N_TXFM_SIZES,
	N_TXFM_MODES
};

// clang-format off
enum TxfmType {
	DCT_DCT,
	DCT_ADST,
	ADST_DCT,
	ADST_ADST,
	N_TXFM_TYPES,
};

enum IntraPredMode {
	VERT_PRED,
	HOR_PRED,
	DC_PRED,
	DIAG_DOWN_LEFT_PRED,
	DIAG_DOWN_RIGHT_PRED,
	VERT_RIGHT_PRED,
	HOR_DOWN_PRED,
	VERT_LEFT_PRED,
	HOR_UP_PRED,
	TM_VP8_PRED,
	LEFT_DC_PRED,
	TOP_DC_PRED,
	DC_128_PRED,
	DC_127_PRED,
	DC_129_PRED,
	N_INTRA_PRED_MODES
};

enum FilterMode {
	FILTER_8TAP_SMOOTH,
	FILTER_8TAP_REGULAR,
	FILTER_8TAP_SHARP,
	FILTER_BILINEAR,
	N_FILTERS,
	FILTER_SWITCHABLE = N_FILTERS,
};

enum BlockPartition {
	PARTITION_NONE,    // [ ] <-.
	PARTITION_H,       // [-]   |
	PARTITION_V,       // [|]   |
	PARTITION_SPLIT,   // [+] --'
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

enum BlockLevel {
    BL_64X64,
    BL_32X32,
    BL_16X16,
    BL_8X8,
};

enum BlockSize {
    BS_64x64,
    BS_64x32,
    BS_32x64,
    BS_32x32,
    BS_32x16,
    BS_16x32,
    BS_16x16,
    BS_16x8,
    BS_8x16,
    BS_8x8,
    BS_8x4,
    BS_4x8,
    BS_4x4,
    N_BS_SIZES,
};

#define DECLARE_ALIGNED(n, t, v) t __attribute__((aligned(n))) v

typedef struct VP9mv {
	DECLARE_ALIGNED(4, int16_t, x);
	int16_t y;
} VP9mv;

typedef struct VP9mvrefPair {
	VP9mv mv[2];
	int8_t ref[2];
} VP9mvrefPair;

#if 0
#define AVERROR_INVALIDDATA -1

typedef struct AVBuffer AVBuffer;
typedef struct AVBufferRef {
	AVBuffer *buffer;
	uint8_t *data;
	int      size;
} AVBufferRef;
#endif

typedef struct ThreadFrame {
	int width;
	int height;
	AVBufferRef *buf[1];
	int key_frame;
} ThreadFrame;

typedef struct VP9Frame {
	ThreadFrame tf;
	void *extradata; ///< RefStruct reference
	uint8_t *segmentation_map;
	VP9mvrefPair *mv;
	int uses_2pass;

	void *hwaccel_picture_private; ///< RefStruct reference
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
	enum TxfmMode txfmmode;
	enum CompPredMode comppredmode;
	struct {
		unsigned log2_tile_cols, log2_tile_rows;
		unsigned tile_cols, tile_rows;
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

#define REF_INVALID_SCALE 0xFFFF

enum MVJoint {
	MV_JOINT_ZERO,
	MV_JOINT_H,
	MV_JOINT_V,
	MV_JOINT_HV,
};

typedef struct ProbContext {
    uint8_t y_mode[4][9];
    uint8_t uv_mode[10][9];
    uint8_t filter[4][2];
    uint8_t mv_mode[7][3];
    uint8_t intra[4];
    uint8_t comp[5];
    uint8_t single_ref[5][2];
    uint8_t comp_ref[5];
    uint8_t tx32p[2][3];
    uint8_t tx16p[2][2];
    uint8_t tx8p[2];
    uint8_t skip[3];
    uint8_t mv_joint[3];
    struct {
        uint8_t sign;
        uint8_t classes[10];
        uint8_t class0;
        uint8_t bits[10];
        uint8_t class0_fp[2][3];
        uint8_t fp[3];
        uint8_t class0_hp;
        uint8_t hp;
    } mv_comp[2];
    uint8_t partition[4][4][3];
} ProbContext;

typedef struct VP9Filter {
    uint8_t level[8 * 8];
    uint8_t /* bit=col */ mask[2 /* 0=y, 1=uv */][2 /* 0=col, 1=row */]
                              [8 /* rows */][4 /* 0=16, 1=8, 2=4, 3=inner4 */];
} VP9Filter;

typedef struct VP9TileData VP9TileData;

typedef struct VPXRangeCoder {
    int high;
    int bits; /* stored negated (i.e. negative "bits" is a positive number of
                 bits left) in order to eliminate a negate in cache refilling */
    const uint8_t *buffer;
    const uint8_t *end;
    unsigned int code_word;
    int end_reached;
} VPXRangeCoder;

typedef struct VP9Context {
	VP9SharedContext s;
	VP9TileData *td;

	struct bitstream gb;
	VPXRangeCoder c;

	int profile;
	unsigned properties;
	int pass, active_tile_cols;

	uint8_t ss_h, ss_v;
	uint8_t last_bpp, bpp_index, bytesperpixel;
	uint8_t last_keyframe;
	// sb_cols/rows, rows/cols and last_fmt are used for allocating all internal
	// arrays, and are thus per-thread. w/h and gf_fmt are synced between threads
	// and are therefore per-stream. pix_fmt represents the value in the header
	// of the currently processed frame.
	int w, h;
	enum AVPixelFormat pix_fmt, last_fmt, gf_fmt;
	enum AVColorSpace colorspace;
	enum AVPixelFormat color_range;
	unsigned sb_cols, sb_rows, rows, cols;
	ThreadFrame next_refs[8];

	struct {
		uint8_t lim_lut[64];
		uint8_t mblim_lut[64];
	} filter_lut;
	struct {
		ProbContext p;
		uint8_t coef[4][2][2][6][6][3];
	} prob_ctx[4];
	struct {
		ProbContext p;
		uint8_t coef[4][2][2][6][6][11];
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
	VP9mv (*above_mv_ctx)[2];

	// whole-frame cache
	uint8_t *intra_pred_data[3];
	VP9Filter *lflvl;

	// block reconstruction intermediates
	int block_alloc_using_2pass;
	uint16_t mvscale[3][2];
	uint8_t mvstep[3][2];

	// frame specific buffer pools
	struct FFRefStructPool *frame_extradata_pool;
	int frame_extradata_pool_size;
} VP9Context;

#endif /* __VP9_SHARED_H__ */
