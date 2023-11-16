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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bs.h"
#include "h2645.h"
#include "h265.h"

#define h265_log(a, ...)   printf("[H265] " a, ##__VA_ARGS__)
#define h265_err(a, ...)   fprintf(stderr, "[H265] " a, ##__VA_ARGS__)
#define h265_field(a, ...) printf("\t" a " = %d\n", ##__VA_ARGS__)

static int h265_decode_nal_vps(void)
{
	h265_log("vps\n");
	return 0;
}

static int h265_decode_nal_sps(void)
{
	h265_log("sps\n");
	return 0;
}

static int h265_decode_nal_pps(void)
{
	h265_log("pps\n");
	return 0;
}

static int h265_decode_nal_sei(void)
{
	h265_log("sei\n");
	return 0;
}

static int h265_decode_slice_header(void)
{
	h265_log("slice\n");
	return 0;
}

static const char *const h265_nal_type_name[64] = {
    "TRAIL_N", // HEVC_NAL_TRAIL_N
    "TRAIL_R", // HEVC_NAL_TRAIL_R
    "TSA_N", // HEVC_NAL_TSA_N
    "TSA_R", // HEVC_NAL_TSA_R
    "STSA_N", // HEVC_NAL_STSA_N
    "STSA_R", // HEVC_NAL_STSA_R
    "RADL_N", // HEVC_NAL_RADL_N
    "RADL_R", // HEVC_NAL_RADL_R
    "RASL_N", // HEVC_NAL_RASL_N
    "RASL_R", // HEVC_NAL_RASL_R
    "RSV_VCL_N10", // HEVC_NAL_VCL_N10
    "RSV_VCL_R11", // HEVC_NAL_VCL_R11
    "RSV_VCL_N12", // HEVC_NAL_VCL_N12
    "RSV_VLC_R13", // HEVC_NAL_VCL_R13
    "RSV_VCL_N14", // HEVC_NAL_VCL_N14
    "RSV_VCL_R15", // HEVC_NAL_VCL_R15
    "BLA_W_LP", // HEVC_NAL_BLA_W_LP
    "BLA_W_RADL", // HEVC_NAL_BLA_W_RADL
    "BLA_N_LP", // HEVC_NAL_BLA_N_LP
    "IDR_W_RADL", // HEVC_NAL_IDR_W_RADL
    "IDR_N_LP", // HEVC_NAL_IDR_N_LP
    "CRA_NUT", // HEVC_NAL_CRA_NUT
    "RSV_IRAP_VCL22", // HEVC_NAL_RSV_IRAP_VCL22
    "RSV_IRAP_VCL23", // HEVC_NAL_RSV_IRAP_VCL23
    "RSV_VCL24", // HEVC_NAL_RSV_VCL24
    "RSV_VCL25", // HEVC_NAL_RSV_VCL25
    "RSV_VCL26", // HEVC_NAL_RSV_VCL26
    "RSV_VCL27", // HEVC_NAL_RSV_VCL27
    "RSV_VCL28", // HEVC_NAL_RSV_VCL28
    "RSV_VCL29", // HEVC_NAL_RSV_VCL29
    "RSV_VCL30", // HEVC_NAL_RSV_VCL30
    "RSV_VCL31", // HEVC_NAL_RSV_VCL31
    "VPS", // HEVC_NAL_VPS
    "SPS", // HEVC_NAL_SPS
    "PPS", // HEVC_NAL_PPS
    "AUD", // HEVC_NAL_AUD
    "EOS_NUT", // HEVC_NAL_EOS_NUT
    "EOB_NUT", // HEVC_NAL_EOB_NUT
    "FD_NUT", // HEVC_NAL_FD_NUT
    "SEI_PREFIX", // HEVC_NAL_SEI_PREFIX
    "SEI_SUFFIX", // HEVC_NAL_SEI_SUFFIX
    "RSV_NVCL41", // HEVC_NAL_RSV_NVCL41
    "RSV_NVCL42", // HEVC_NAL_RSV_NVCL42
    "RSV_NVCL43", // HEVC_NAL_RSV_NVCL43
    "RSV_NVCL44", // HEVC_NAL_RSV_NVCL44
    "RSV_NVCL45", // HEVC_NAL_RSV_NVCL45
    "RSV_NVCL46", // HEVC_NAL_RSV_NVCL46
    "RSV_NVCL47", // HEVC_NAL_RSV_NVCL47
    "UNSPEC48", // HEVC_NAL_UNSPEC48
    "UNSPEC49", // HEVC_NAL_UNSPEC49
    "UNSPEC50", // HEVC_NAL_UNSPEC50
    "UNSPEC51", // HEVC_NAL_UNSPEC51
    "UNSPEC52", // HEVC_NAL_UNSPEC52
    "UNSPEC53", // HEVC_NAL_UNSPEC53
    "UNSPEC54", // HEVC_NAL_UNSPEC54
    "UNSPEC55", // HEVC_NAL_UNSPEC55
    "UNSPEC56", // HEVC_NAL_UNSPEC56
    "UNSPEC57", // HEVC_NAL_UNSPEC57
    "UNSPEC58", // HEVC_NAL_UNSPEC58
    "UNSPEC59", // HEVC_NAL_UNSPEC59
    "UNSPEC60", // HEVC_NAL_UNSPEC60
    "UNSPEC61", // HEVC_NAL_UNSPEC61
    "UNSPEC62", // HEVC_NAL_UNSPEC62
    "UNSPEC63", // HEVC_NAL_UNSPEC63
};

static const char *h265_nal_unit_name(int nal_type)
{
	return h265_nal_type_name[nal_type];
}

int h265_decode_nal_unit(struct h265_context *s, uint8_t *buf, int size)
{
	struct bitstream *gb = NULL;
	uint64_t start_pos, end_pos;
	int err;

	int nal_size = size;
	int rbsp_size = size;
	uint8_t *rbsp_buf = (uint8_t *)calloc(1, size);
	if (!rbsp_buf)
		return -1;

	err = h2645_nal_to_rbsp(buf, &nal_size, rbsp_buf, &rbsp_size);
	if (err < 0) {
		h265_err("failed to convert NAL to RBSP\n");
		goto free_rbsp;
	}

	bs_init(&s->gb, rbsp_buf, rbsp_size);
	gb = &s->gb;
	start_pos = (((uint64_t)(void *)gb->p) * 8) + (8 - gb->bits_left);
	if (get_bits1(gb) != 0) {
		h265_err("forbidden bit != 0\n");
		goto exit;
	}

	s->nal_unit_type = get_bits(gb, 6);
	s->nuh_layer_id = get_bits(gb, 6);
	s->temporal_id = get_bits(gb, 3) - 1;
	if (s->temporal_id < 0) {
		h265_err("temporal_id < 0\n");
		goto exit;
	}

	printf("H265_%s (%d) {\n", h265_nal_unit_name(s->nal_unit_type), s->nal_unit_type);
	h265_field("nal_unit_type", s->nal_unit_type);
	h265_field("nuh_layer_id", s->nuh_layer_id);
	h265_field("temporal_id", s->temporal_id);

	switch (s->nal_unit_type) {
	case HEVC_NAL_VPS:
		err = h265_decode_nal_vps();
		if (err < 0)
			goto exit;
		break;
	case HEVC_NAL_SPS:
		err = h265_decode_nal_sps();
		if (err < 0)
			goto exit;
		break;
	case HEVC_NAL_PPS:
		err = h265_decode_nal_pps();
		if (err < 0)
			goto exit;
		break;
	case HEVC_NAL_SEI_PREFIX:
	case HEVC_NAL_SEI_SUFFIX:
		err = h265_decode_nal_sei();
		if (err < 0)
			goto exit;
		break;
	case HEVC_NAL_TRAIL_R:
	case HEVC_NAL_TRAIL_N:
	case HEVC_NAL_TSA_N:
	case HEVC_NAL_TSA_R:
	case HEVC_NAL_STSA_N:
	case HEVC_NAL_STSA_R:
	case HEVC_NAL_BLA_W_LP:
	case HEVC_NAL_BLA_W_RADL:
	case HEVC_NAL_BLA_N_LP:
	case HEVC_NAL_IDR_W_RADL:
	case HEVC_NAL_IDR_N_LP:
	case HEVC_NAL_CRA_NUT:
	case HEVC_NAL_RADL_N:
	case HEVC_NAL_RADL_R:
	case HEVC_NAL_RASL_N:
	case HEVC_NAL_RASL_R:
		err = h265_decode_slice_header();
		if (err < 0)
			goto exit;
		break;
	case HEVC_NAL_EOS_NUT:
	case HEVC_NAL_EOB_NUT:
		break;
	case HEVC_NAL_AUD:
	case HEVC_NAL_FD_NUT:
	case HEVC_NAL_UNSPEC62:
		break;
	default:
		h265_log("Skipping NAL unit %d\n", s->nal_unit_type);
	}

	printf("}\n\n");

exit:
free_rbsp:
	free(rbsp_buf);
	return 0;
}
