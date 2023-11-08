/*
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

#ifndef AVCODEC_VP9DATA_H
#define AVCODEC_VP9DATA_H

#include <stdint.h>

extern const int16_t ff_vp9_dc_qlookup[3][256];
extern const int16_t ff_vp9_ac_qlookup[3][256];
extern const uint8_t ff_vp9_default_coef_probs[4][2][2][6][6][3];
extern const uint8_t vp9_kf_y_mode_probs[10][10][9];
extern const uint8_t vp9_kf_uv_mode_probs[10][9];
extern const uint8_t vp9_default_if_y_probs[4][9];
extern const uint8_t vp9_default_if_uv_probs[10][9];
extern const uint8_t vp9_default_partition_probs[16][3];
extern const uint8_t vp9_kf_partition_probs[16][3];

#endif /* AVCODEC_VP9DATA_H */
