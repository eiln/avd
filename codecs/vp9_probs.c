/*
 *  Copyright (c) 2010 The WebM project authors. All Rights Reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#include <assert.h>

#include "vp9_probs.h"
#include "vpx_dsp_common.h"

#define TREE_SIZE(leaf_count) (2 * (leaf_count)-2)

#define DC_PRED 0    // Average of above and left pixels
#define V_PRED 1     // Vertical
#define H_PRED 2     // Horizontal
#define D45_PRED 3   // Directional 45  deg = round(arctan(1/1) * 180/pi)
#define D135_PRED 4  // Directional 135 deg = 180 - 45
#define D117_PRED 5  // Directional 117 deg = 180 - 63
#define D153_PRED 6  // Directional 153 deg = 180 - 27
#define D207_PRED 7  // Directional 207 deg = 180 + 27
#define D63_PRED 8   // Directional 63  deg = round(arctan(2/1) * 180/pi)
#define TM_PRED 9    // True-motion
#define NEARESTMV 10
#define NEARMV 11
#define ZEROMV 12
#define NEWMV 13
#define MB_MODE_COUNT 14
typedef uint8_t PREDICTION_MODE;

#define INTRA_MODES (TM_PRED + 1)

#define INTER_MODES (1 + NEWMV - NEARESTMV)

#define SKIP_CONTEXTS 3
#define INTER_MODE_CONTEXTS 7

#define INTER_OFFSET(mode) ((mode)-NEARESTMV)

#define EIGHTTAP 0
#define EIGHTTAP_SMOOTH 1
#define EIGHTTAP_SHARP 2
#define SWITCHABLE_FILTERS 3 /* Number of switchable filters */
#define BILINEAR 3
#define FOURTAP 4
// The codec can operate in four possible inter prediction filter mode:
// 8-tap, 8-tap-smooth, 8-tap-sharp, and switching between the three.
#define SWITCHABLE_FILTER_CONTEXTS (SWITCHABLE_FILTERS + 1)
#define SWITCHABLE 4 /* should be the last one */

typedef enum PARTITION_TYPE {
  PARTITION_NONE,
  PARTITION_HORZ,
  PARTITION_VERT,
  PARTITION_SPLIT,
  PARTITION_TYPES,
  PARTITION_INVALID = PARTITION_TYPES
} PARTITION_TYPE;

/* Array indices are identical to previously-existing INTRAMODECONTEXTNODES. */
static const int8_t vp9_intra_mode_tree[TREE_SIZE(INTRA_MODES)] = {
  -DC_PRED,   2,          /* 0 = DC_NODE */
  -TM_PRED,   4,          /* 1 = TM_NODE */
  -V_PRED,    6,          /* 2 = V_NODE */
  8,          12,         /* 3 = COM_NODE */
  -H_PRED,    10,         /* 4 = H_NODE */
  -D135_PRED, -D117_PRED, /* 5 = D135_NODE */
  -D45_PRED,  14,         /* 6 = D45_NODE */
  -D63_PRED,  16,         /* 7 = D63_NODE */
  -D153_PRED, -D207_PRED  /* 8 = D153_NODE */
};

static const int8_t vp9_inter_mode_tree[TREE_SIZE(INTER_MODES)] = {
  -INTER_OFFSET(ZEROMV), 2, -INTER_OFFSET(NEARESTMV), 4, -INTER_OFFSET(NEARMV),
  -INTER_OFFSET(NEWMV)
};

static const int8_t vp9_partition_tree[TREE_SIZE(PARTITION_TYPES)] = {
  -PARTITION_NONE, 2, -PARTITION_HORZ, 4, -PARTITION_VERT, -PARTITION_SPLIT
};

static const int8_t vp9_switchable_interp_tree[TREE_SIZE(
    SWITCHABLE_FILTERS)] = { -EIGHTTAP, 2, -EIGHTTAP_SMOOTH, -EIGHTTAP_SHARP };

/* This function assumes prob1 and prob2 are already within [1,255] range. */
static inline uint8_t weighted_prob(int prob1, int prob2, int factor)
{
    return ROUND_POWER_OF_TWO(prob1 * (256 - factor) + prob2 * factor, 8);
}

static inline uint8_t get_prob(unsigned int num, unsigned int den)
{
    assert(den != 0);
    {
        const int p = (int)(((uint64_t)num * 256 + (den >> 1)) / den);
        // (p > 255) ? 255 : (p < 1) ? 1 : p;
        const int clipped_prob = p | ((255 - p) >> 23) | (p == 0);
        return (uint8_t)clipped_prob;
    }
}

// MODE_MV_MAX_UPDATE_FACTOR (128) * count / MODE_MV_COUNT_SAT;
static const int count_to_update_factor[21] = {
    0,  6,  12, 19, 25, 32,  38,  44,  51,  57, 64,
    70, 76, 83, 89, 96, 102, 108, 115, 121, 128
};

static inline uint8_t mode_mv_merge_probs(uint8_t pre_prob,
                                           const unsigned int ct[2])
{
    const unsigned int den = ct[0] + ct[1];
    if (den == 0) {
        return pre_prob;
    } else {
        const unsigned int count = VPXMIN(den, 20);
        const unsigned int factor = count_to_update_factor[count];
        const uint8_t prob = get_prob(ct[0], den);
        return weighted_prob(pre_prob, prob, factor);
    }
}

static unsigned int tree_merge_probs_impl(unsigned int i,
                                          const int8_t *tree,
                                          const uint8_t *pre_probs,
                                          const unsigned int *counts,
                                          uint8_t *probs) {
  const int l = tree[i];
  const unsigned int left_count =
      (l <= 0) ? counts[-l]
               : tree_merge_probs_impl(l, tree, pre_probs, counts, probs);
  const int r = tree[i + 1];
  const unsigned int right_count =
      (r <= 0) ? counts[-r]
               : tree_merge_probs_impl(r, tree, pre_probs, counts, probs);
  const unsigned int ct[2] = { left_count, right_count };
  probs[i >> 1] = mode_mv_merge_probs(pre_probs[i >> 1], ct);
  return left_count + right_count;
}

static void vpx_tree_merge_probs(const int8_t *tree, const uint8_t *pre_probs,
                          const unsigned int *counts, uint8_t *probs)
{
    tree_merge_probs_impl(0, tree, pre_probs, counts, probs);
}

static void tx_counts_to_branch_counts_32x32(const unsigned int *tx_count_32x32p,
                                      unsigned int (*ct_32x32p)[2]) {
  ct_32x32p[0][0] = tx_count_32x32p[TX_4X4];
  ct_32x32p[0][1] = tx_count_32x32p[TX_8X8] + tx_count_32x32p[TX_16X16] +
                    tx_count_32x32p[TX_32X32];
  ct_32x32p[1][0] = tx_count_32x32p[TX_8X8];
  ct_32x32p[1][1] = tx_count_32x32p[TX_16X16] + tx_count_32x32p[TX_32X32];
  ct_32x32p[2][0] = tx_count_32x32p[TX_16X16];
  ct_32x32p[2][1] = tx_count_32x32p[TX_32X32];
}

static void tx_counts_to_branch_counts_16x16(const unsigned int *tx_count_16x16p,
                                      unsigned int (*ct_16x16p)[2]) {
  ct_16x16p[0][0] = tx_count_16x16p[TX_4X4];
  ct_16x16p[0][1] = tx_count_16x16p[TX_8X8] + tx_count_16x16p[TX_16X16];
  ct_16x16p[1][0] = tx_count_16x16p[TX_8X8];
  ct_16x16p[1][1] = tx_count_16x16p[TX_16X16];
}

static void tx_counts_to_branch_counts_8x8(const unsigned int *tx_count_8x8p,
                                    unsigned int (*ct_8x8p)[2]) {
  ct_8x8p[0][0] = tx_count_8x8p[TX_4X4];
  ct_8x8p[0][1] = tx_count_8x8p[TX_8X8];
}

static void vp9_adapt_mode_probs(VP9Context *s)
{
    VP9ProbContext *pp = &s->prob_ctx[s->s.h.framectxid].p;
    VP9ProbContext *p = &s->prob.p;
    VP9FrameCounts *counts = &s->counts;
    int i, j;

    for (i = 0; i < 4; i++)
        p->intra_inter[i] = mode_mv_merge_probs(pp->intra_inter[i],
                                                  counts->intra_inter[i]);

    for (i = 0; i < 5; i++)
        p->comp_inter[i] = mode_mv_merge_probs(pp->comp_inter[i],
                    counts->comp_inter[i]);

    for (i = 0; i < 5; i++)
        p->comp_ref[i] = mode_mv_merge_probs(pp->comp_ref[i],
                    counts->comp_ref[i]);

    for (i = 0; i < 5; i++)
        for (j = 0; j < 2; j++)
            p->single_ref[i][j] = mode_mv_merge_probs(pp->single_ref[i][j],
                                                  counts->single_ref[i][j]);

  for (i = 0; i < INTER_MODE_CONTEXTS; i++)
    vpx_tree_merge_probs(vp9_inter_mode_tree, pp->inter_mode[i],
                         counts->inter_mode[i], p->inter_mode[i]);

  for (i = 0; i < 4; i++)
    vpx_tree_merge_probs(vp9_intra_mode_tree, pp->y_mode[i],
                         counts->y_mode[i], p->y_mode[i]);

  for (i = 0; i < 10; ++i)
    vpx_tree_merge_probs(vp9_intra_mode_tree, pp->uv_mode[i],
                         counts->uv_mode[i], p->uv_mode[i]);

  for (i = 0; i < 16; i++)
    vpx_tree_merge_probs(vp9_partition_tree, pp->partition[i],
                         counts->partition[i], p->partition[i]);

  if (s->s.h.filtermode == FILTER_SWITCHABLE) {
    for (i = 0; i < SWITCHABLE_FILTER_CONTEXTS; i++)
      vpx_tree_merge_probs(
          vp9_switchable_interp_tree, pp->switchable_interp[i],
          counts->switchable_interp[i], p->switchable_interp[i]);
  }

  if (s->s.h.txfmmode == TX_MODE_SELECT) {
    unsigned int branch_ct_8x8p[TX_SIZES - 3][2];
    unsigned int branch_ct_16x16p[TX_SIZES - 2][2];
    unsigned int branch_ct_32x32p[TX_SIZES - 1][2];

    for (i = 0; i < 2; ++i) {
      tx_counts_to_branch_counts_8x8(counts->tx.p8x8[i], branch_ct_8x8p);
      for (j = 0; j < TX_SIZES - 3; ++j)
        p->tx.p8x8[i][j] =
            mode_mv_merge_probs(pp->tx.p8x8[i][j], branch_ct_8x8p[j]);

      tx_counts_to_branch_counts_16x16(counts->tx.p16x16[i], branch_ct_16x16p);
      for (j = 0; j < TX_SIZES - 2; ++j)
        p->tx.p16x16[i][j] = mode_mv_merge_probs(
            pp->tx.p16x16[i][j], branch_ct_16x16p[j]);

      tx_counts_to_branch_counts_32x32(counts->tx.p32x32[i], branch_ct_32x32p);
      for (j = 0; j < TX_SIZES - 1; ++j)
        p->tx.p32x32[i][j] = mode_mv_merge_probs(
            pp->tx.p32x32[i][j], branch_ct_32x32p[j]);
    }
  }

  for (i = 0; i < SKIP_CONTEXTS; ++i)
    p->skip[i] = mode_mv_merge_probs(pp->skip[i], counts->skip[i]);

}

// Coefficient token alphabet
#define ZERO_TOKEN 0        // 0     Extra Bits 0+0
#define ONE_TOKEN 1         // 1     Extra Bits 0+1
#define TWO_TOKEN 2         // 2     Extra Bits 0+1
#define THREE_TOKEN 3       // 3     Extra Bits 0+1
#define FOUR_TOKEN 4        // 4     Extra Bits 0+1
#define CATEGORY1_TOKEN 5   // 5-6   Extra Bits 1+1
#define CATEGORY2_TOKEN 6   // 7-10  Extra Bits 2+1
#define CATEGORY3_TOKEN 7   // 11-18 Extra Bits 3+1
#define CATEGORY4_TOKEN 8   // 19-34 Extra Bits 4+1
#define CATEGORY5_TOKEN 9   // 35-66 Extra Bits 5+1
#define CATEGORY6_TOKEN 10  // 67+   Extra Bits 14+1
#define EOB_TOKEN 11        // EOB   Extra Bits 0+0

#define EOB_MODEL_TOKEN 3

#define COEF_COUNT_SAT 24
#define COEF_MAX_UPDATE_FACTOR 112
#define COEF_COUNT_SAT_KEY 24
#define COEF_MAX_UPDATE_FACTOR_KEY 112
#define COEF_COUNT_SAT_AFTER_KEY 24
#define COEF_MAX_UPDATE_FACTOR_AFTER_KEY 128

static inline uint8_t get_binary_prob(unsigned int n0, unsigned int n1) {
  const unsigned int den = n0 + n1;
  if (den == 0) return 128u;
  return get_prob(n0, den);
}

static inline uint8_t merge_probs(uint8_t pre_prob, const unsigned int ct[2],
                                   unsigned int count_sat,
                                   unsigned int max_update_factor) {
  const uint8_t prob = get_binary_prob(ct[0], ct[1]);
  const unsigned int count = VPXMIN(ct[0] + ct[1], count_sat);
  const unsigned int factor = max_update_factor * count / count_sat;
  return weighted_prob(pre_prob, prob, factor);
}

static void adapt_coef_probs(VP9Context *s, int tx_size,
                             unsigned int count_sat,
                             unsigned int update_factor) {
    VP9ProbContext *pp = &s->prob_ctx[s->s.h.framectxid].p;
    vp9_coeff_probs_model *const pre_probs = pp->coef[tx_size];
    vp9_coeff_probs_model *const probs = s->prob.p.coef[tx_size];
    vp9_coeff_count_model *counts = s->counts.coef[tx_size];
    unsigned int(*eob_counts)[REF_TYPES][COEF_BANDS][COEFF_CONTEXTS] = s->counts.eob_branch[tx_size];
    int i, j, k, l, m;

  for (i = 0; i < PLANE_TYPES; ++i)
    for (j = 0; j < REF_TYPES; ++j)
      for (k = 0; k < COEF_BANDS; ++k)
        for (l = 0; l < BAND_COEFF_CONTEXTS(k); ++l) {
          const int n0 = counts[i][j][k][l][ZERO_TOKEN];
          const int n1 = counts[i][j][k][l][ONE_TOKEN];
          const int n2 = counts[i][j][k][l][TWO_TOKEN];
          const int neob = counts[i][j][k][l][EOB_MODEL_TOKEN];
          const unsigned int branch_ct[UNCONSTRAINED_NODES][2] = {
            { neob, eob_counts[i][j][k][l] - neob }, { n0, n1 + n2 }, { n1, n2 }
          };
          for (m = 0; m < UNCONSTRAINED_NODES; ++m)
            probs[i][j][k][l][m] =
                merge_probs(pre_probs[i][j][k][l][m], branch_ct[m], count_sat,
                            update_factor);
        }
}

static void vp9_adapt_coef_probs(VP9Context *s) {
  unsigned int count_sat, update_factor;

  if (s->s.h.keyframe || s->s.h.intraonly) {
    update_factor = COEF_MAX_UPDATE_FACTOR_KEY;
    count_sat = COEF_COUNT_SAT_KEY;
  } else if (s->last_keyframe) {
    update_factor = COEF_MAX_UPDATE_FACTOR_AFTER_KEY; /* adapt quickly */
    count_sat = COEF_COUNT_SAT_AFTER_KEY;
  } else {
    update_factor = COEF_MAX_UPDATE_FACTOR;
    count_sat = COEF_COUNT_SAT;
  }
  for (int t = TX_4X4; t <= TX_32X32; t++)
    adapt_coef_probs(s, t, count_sat, update_factor);
}

/* mv stuff */

#define MV_JOINTS 4
typedef enum {
  MV_JOINT_ZERO = 0,   /* Zero vector */
  MV_JOINT_HNZVZ = 1,  /* Vert zero, hor nonzero */
  MV_JOINT_HZVNZ = 2,  /* Hor zero, vert nonzero */
  MV_JOINT_HNZVNZ = 3, /* Both components nonzero */
} MV_JOINT_TYPE;

static inline int mv_joint_vertical(MV_JOINT_TYPE type) {
  return type == MV_JOINT_HZVNZ || type == MV_JOINT_HNZVNZ;
}

static inline int mv_joint_horizontal(MV_JOINT_TYPE type) {
  return type == MV_JOINT_HNZVZ || type == MV_JOINT_HNZVNZ;
}

/* Symbols for coding magnitude class of nonzero components */
#define MV_CLASSES 11
typedef enum {
  MV_CLASS_0 = 0,   /* (0, 2]     integer pel */
  MV_CLASS_1 = 1,   /* (2, 4]     integer pel */
  MV_CLASS_2 = 2,   /* (4, 8]     integer pel */
  MV_CLASS_3 = 3,   /* (8, 16]    integer pel */
  MV_CLASS_4 = 4,   /* (16, 32]   integer pel */
  MV_CLASS_5 = 5,   /* (32, 64]   integer pel */
  MV_CLASS_6 = 6,   /* (64, 128]  integer pel */
  MV_CLASS_7 = 7,   /* (128, 256] integer pel */
  MV_CLASS_8 = 8,   /* (256, 512] integer pel */
  MV_CLASS_9 = 9,   /* (512, 1024] integer pel */
  MV_CLASS_10 = 10, /* (1024,2048] integer pel */
} MV_CLASS_TYPE;

static const int8_t vp9_mv_joint_tree[TREE_SIZE(MV_JOINTS)] = {
  -MV_JOINT_ZERO, 2, -MV_JOINT_HNZVZ, 4, -MV_JOINT_HZVNZ, -MV_JOINT_HNZVNZ
};

static const int8_t vp9_mv_class_tree[TREE_SIZE(MV_CLASSES)] = {
  -MV_CLASS_0, 2,           -MV_CLASS_1, 4,           6,
  8,           -MV_CLASS_2, -MV_CLASS_3, 10,          12,
  -MV_CLASS_4, -MV_CLASS_5, -MV_CLASS_6, 14,          16,
  18,          -MV_CLASS_7, -MV_CLASS_8, -MV_CLASS_9, -MV_CLASS_10,
};

static const int8_t vp9_mv_class0_tree[TREE_SIZE(CLASS0_SIZE)] = { -0, -1 };

static const int8_t vp9_mv_fp_tree[TREE_SIZE(MV_FP_SIZE)] = { -0, 2,  -1,
                                                               4,  -2, -3 };

static void vp9_adapt_mv_probs(VP9Context *s, int allow_hp) {
  int i, j;

  nmv_context *fc = &s->prob.p.nmvc;
  const nmv_context *pre_fc = &s->prob_ctx[s->s.h.framectxid].p.nmvc;
  const nmv_context_counts *counts = &s->counts.mv;

  vpx_tree_merge_probs(vp9_mv_joint_tree, pre_fc->joints, counts->joints,
                       fc->joints);

  for (i = 0; i < 2; ++i) {
    nmv_component *comp = &fc->comps[i];
    const nmv_component *pre_comp = &pre_fc->comps[i];
    const nmv_component_counts *c = &counts->comps[i];

    comp->sign = mode_mv_merge_probs(pre_comp->sign, c->sign);
    vpx_tree_merge_probs(vp9_mv_class_tree, pre_comp->classes, c->classes,
                         comp->classes);
    vpx_tree_merge_probs(vp9_mv_class0_tree, pre_comp->class0, c->class0,
                         comp->class0);

    for (j = 0; j < MV_OFFSET_BITS; ++j)
      comp->bits[j] = mode_mv_merge_probs(pre_comp->bits[j], c->bits[j]);

    for (j = 0; j < CLASS0_SIZE; ++j)
      vpx_tree_merge_probs(vp9_mv_fp_tree, pre_comp->class0_fp[j],
                           c->class0_fp[j], comp->class0_fp[j]);

    vpx_tree_merge_probs(vp9_mv_fp_tree, pre_comp->fp, c->fp, comp->fp);

    if (allow_hp) {
      comp->class0_hp = mode_mv_merge_probs(pre_comp->class0_hp, c->class0_hp);
      comp->hp = mode_mv_merge_probs(pre_comp->hp, c->hp);
    }
  }
}

void vp9_adapt_probs(VP9Context *s)
{
    vp9_adapt_coef_probs(s);
    if (!s->s.h.keyframe && !s->s.h.intraonly) {
        vp9_adapt_mode_probs(s);
        vp9_adapt_mv_probs(s, s->s.h.highprecisionmvs);
    }

    if (!s->s.h.parallelmode)
        s->prob_ctx[s->s.h.framectxid].p = s->prob.p;
}
