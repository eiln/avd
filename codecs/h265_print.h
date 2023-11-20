
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

#ifndef __H265_PRINT_H__
#define __H265_PRINT_H__

#include <stdio.h>

#define h265_log(a, ...)   printf("[H265] " a, ##__VA_ARGS__)
#define h265_wrn(a, ...)   fprintf(stderr, "[H265][WRN]" a, ##__VA_ARGS__)
#define h265_err(a, ...)   fprintf(stderr, "[H265][ERR]" a, ##__VA_ARGS__)

// I dont know how to do macros
#define H265_PRINT_PREFIX "\t"
#define h265_field(a, ...)     printf(H265_PRINT_PREFIX a " = %d\n", ##__VA_ARGS__)
#define h265_fieldl(a, ...)    printf(H265_PRINT_PREFIX a " = %ld\n", ##__VA_ARGS__)
#define h265_fieldt(a, ...)    printf(H265_PRINT_PREFIX H265_PRINT_PREFIX a " = %d\n", ##__VA_ARGS__)
#define h265_field2(a, b, ...) printf(H265_PRINT_PREFIX a " = %d [%s]\n", b, ##__VA_ARGS__)
#define h265_header(a, ...)    printf(H265_PRINT_PREFIX a "\n", ##__VA_ARGS__)

void h265_print_nal_vps(struct hevc_vps *vps);
void h265_print_nal_sps(struct hevc_sps *sps);
void h265_print_nal_pps(struct hevc_pps *pps);
void h265_print_nal_slice_header(struct h265_context *s, struct hevc_slice_header *sh);

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

static inline const char *h265_nal_unit_name(int nal_type)
{
	return h265_nal_type_name[nal_type];
}

#endif /* __H265_PRINT_H__ */
