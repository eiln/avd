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

#ifndef __H265_H__
#define __H265_H__

#include <stdint.h>
#include "bs.h"

/**
 * Table 7-1 – NAL unit type codes and NAL unit type classes in
 * T-REC-H.265-201802
 */
enum HEVCNALUnitType {
	HEVC_NAL_TRAIL_N        = 0,
	HEVC_NAL_TRAIL_R        = 1,
	HEVC_NAL_TSA_N          = 2,
	HEVC_NAL_TSA_R          = 3,
	HEVC_NAL_STSA_N         = 4,
	HEVC_NAL_STSA_R         = 5,
	HEVC_NAL_RADL_N         = 6,
	HEVC_NAL_RADL_R         = 7,
	HEVC_NAL_RASL_N         = 8,
	HEVC_NAL_RASL_R         = 9,
	HEVC_NAL_VCL_N10        = 10,
	HEVC_NAL_VCL_R11        = 11,
	HEVC_NAL_VCL_N12        = 12,
	HEVC_NAL_VCL_R13        = 13,
	HEVC_NAL_VCL_N14        = 14,
	HEVC_NAL_VCL_R15        = 15,
	HEVC_NAL_BLA_W_LP       = 16,
	HEVC_NAL_BLA_W_RADL     = 17,
	HEVC_NAL_BLA_N_LP       = 18,
	HEVC_NAL_IDR_W_RADL     = 19,
	HEVC_NAL_IDR_N_LP       = 20,
	HEVC_NAL_CRA_NUT        = 21,
	HEVC_NAL_RSV_IRAP_VCL22 = 22,
	HEVC_NAL_RSV_IRAP_VCL23 = 23,
	HEVC_NAL_RSV_VCL24      = 24,
	HEVC_NAL_RSV_VCL25      = 25,
	HEVC_NAL_RSV_VCL26      = 26,
	HEVC_NAL_RSV_VCL27      = 27,
	HEVC_NAL_RSV_VCL28      = 28,
	HEVC_NAL_RSV_VCL29      = 29,
	HEVC_NAL_RSV_VCL30      = 30,
	HEVC_NAL_RSV_VCL31      = 31,
	HEVC_NAL_VPS            = 32,
	HEVC_NAL_SPS            = 33,
	HEVC_NAL_PPS            = 34,
	HEVC_NAL_AUD            = 35,
	HEVC_NAL_EOS_NUT        = 36,
	HEVC_NAL_EOB_NUT        = 37,
	HEVC_NAL_FD_NUT         = 38,
	HEVC_NAL_SEI_PREFIX     = 39,
	HEVC_NAL_SEI_SUFFIX     = 40,
	HEVC_NAL_RSV_NVCL41     = 41,
	HEVC_NAL_RSV_NVCL42     = 42,
	HEVC_NAL_RSV_NVCL43     = 43,
	HEVC_NAL_RSV_NVCL44     = 44,
	HEVC_NAL_RSV_NVCL45     = 45,
	HEVC_NAL_RSV_NVCL46     = 46,
	HEVC_NAL_RSV_NVCL47     = 47,
	HEVC_NAL_UNSPEC48       = 48,
	HEVC_NAL_UNSPEC49       = 49,
	HEVC_NAL_UNSPEC50       = 50,
	HEVC_NAL_UNSPEC51       = 51,
	HEVC_NAL_UNSPEC52       = 52,
	HEVC_NAL_UNSPEC53       = 53,
	HEVC_NAL_UNSPEC54       = 54,
	HEVC_NAL_UNSPEC55       = 55,
	HEVC_NAL_UNSPEC56       = 56,
	HEVC_NAL_UNSPEC57       = 57,
	HEVC_NAL_UNSPEC58       = 58,
	HEVC_NAL_UNSPEC59       = 59,
	HEVC_NAL_UNSPEC60       = 60,
	HEVC_NAL_UNSPEC61       = 61,
	HEVC_NAL_UNSPEC62       = 62,
	HEVC_NAL_UNSPEC63       = 63,
};

struct h265_context {
	int nal_unit_type;
	int nuh_layer_id;
	int temporal_id;
	struct bitstream gb;
};

int h265_decode_nal_unit(struct h265_context *ctx, uint8_t *buf, int size);

#endif /* __H265_H__ */
