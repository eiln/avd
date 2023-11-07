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

#ifndef __VP9_PROBS_H__
#define __VP9_PROBS_H__

#include <stdint.h>
#include "vp9_dec.h"

static const uint8_t default_inter_mode_probs[7][3] = {
	{ 2, 173, 34 },  // 0 = both zero mv
	{ 7, 145, 85 },  // 1 = one zero mv + one a predicted mv
	{ 7, 166, 63 },  // 2 = two predicted mvs
	{ 7, 94, 66 },   // 3 = one predicted/zero and one new mv
	{ 8, 64, 46 },   // 4 = two new mvs
	{ 17, 81, 31 },  // 5 = one intra neighbour + x
	{ 25, 29, 30 },  // 6 = two intra neighbours
};

static const uint8_t default_intra_inter_p[4] = {
    9, 102, 187, 225,
};

static const uint8_t default_comp_inter_p[5] = {
    239, 183, 119, 96, 41,
};

static const uint8_t default_comp_ref_p[5] = {
    50, 126, 123, 221, 226,
};

static const uint8_t default_single_ref_p[5][2] = {
	{ 33, 16 }, { 77, 74 }, { 142, 142 }, { 172, 170 }, { 238, 247 }
};

static const struct tx_probs default_tx_probs = { { { 3, 136, 37 },
                                                    { 5, 52, 13 } },
                                                  { { 20, 152 }, { 15, 101 } },
                                                  { { 100 }, { 66 } } };

static const uint8_t default_skip_probs[3] = {
	192, 128, 64
};

static const uint8_t default_switchable_interp_prob[4][2] = {
	{ 235, 162 },
	{ 36,  255 },
	{ 34,    3 },
	{ 149, 144 },
};

static const nmv_context default_nmv_context = {
  { 32, 64, 96 },
  { {
        // Vertical component
        128,                                                   // sign
        { 224, 144, 192, 168, 192, 176, 192, 198, 198, 245 },  // class
        { 216 },                                               // class0
        { 136, 140, 148, 160, 176, 192, 224, 234, 234, 240 },  // bits
        { { 128, 128, 64 }, { 96, 112, 64 } },                 // class0_fp
        { 64, 96, 64 },                                        // fp
        160,                                                   // class0_hp bit
        128,                                                   // hp
    },
    {
        // Horizontal component
        128,                                                   // sign
        { 216, 128, 176, 160, 176, 176, 192, 198, 198, 208 },  // class
        { 208 },                                               // class0
        { 136, 140, 148, 160, 176, 192, 224, 234, 234, 240 },  // bits
        { { 128, 128, 64 }, { 96, 112, 64 } },                 // class0_fp
        { 64, 96, 64 },                                        // fp
        160,                                                   // class0_hp bit
        128,                                                   // hp
    } },
};

void vp9_adapt_probs(VP9Context *s);

#endif /* __VP9_PROBS_H__ */
