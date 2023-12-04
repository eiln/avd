/*
 * Copyright 2023 Eileen Yoon <eyn@gmx.com>
 *
 * Based on envytools, libavcodec
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
#include "h264.h"
#include "h2645.h"
#include "util.h"

#define h264_log(a, ...)  printf("[H264] " a, ##__VA_ARGS__)
#define h264_err(a, ...)  fprintf(stderr, "[H264] " a, ##__VA_ARGS__)

static const uint8_t h264_avd_zigzag_scan4x4[16+1] = {
	0 + 0 * 4, 1 + 0 * 4, 0 + 1 * 4, 0 + 2 * 4,
	1 + 1 * 4, 2 + 0 * 4, 3 + 0 * 4, 2 + 1 * 4,
	1 + 2 * 4, 0 + 3 * 4, 1 + 3 * 4, 2 + 2 * 4,
	3 + 1 * 4, 3 + 2 * 4, 2 + 3 * 4, 3 + 3 * 4,
};

static const uint8_t h264_avd_zigzag_scan8x8[64+1] = {
	0 +  0 * 4,  1 +  0 * 4,  0 +  1 * 4,  0 +  2 * 4,
	1 +  1 * 4,  2 +  0 * 4,  3 +  0 * 4,  2 +  1 * 4,
	1 +  2 * 4,  0 +  3 * 4,  0 +  8 * 4,  1 +  3 * 4,
	2 +  2 * 4,  3 +  1 * 4,  0 +  4 * 4,  1 +  4 * 4,
	0 +  5 * 4,  3 +  2 * 4,  2 +  3 * 4,  1 +  8 * 4,
	0 +  9 * 4,  0 + 10 * 4,  1 +  9 * 4,  2 +  8 * 4,
	3 +  3 * 4,  0 +  6 * 4,  1 +  5 * 4,  2 +  4 * 4,
	3 +  4 * 4,  2 +  5 * 4,  1 +  6 * 4,  0 +  7 * 4,
	3 +  8 * 4,  2 +  9 * 4,  1 + 10 * 4,  0 + 11 * 4,
	1 + 11 * 4,  2 + 10 * 4,  3 +  9 * 4,  0 + 12 * 4,
	1 +  7 * 4,  2 +  6 * 4,  3 +  5 * 4,  3 +  6 * 4,
	2 +  7 * 4,  1 + 12 * 4,  0 + 13 * 4,  3 + 10 * 4,
	2 + 11 * 4,  3 + 11 * 4,  0 + 14 * 4,  1 + 13 * 4,
	2 + 12 * 4,  3 +  7 * 4,  3 + 12 * 4,  2 + 13 * 4,
	1 + 14 * 4,  0 + 15 * 4,  1 + 15 * 4,  2 + 14 * 4,
	3 + 13 * 4,  3 + 14 * 4,  2 + 15 * 4,  3 + 15 * 4,
};

static const uint8_t default_scaling4[2][16] = {
	{  6, 13, 20, 28, 13, 20, 28, 32,
	  20, 28, 32, 37, 28, 32, 37, 42 },
	{ 10, 14, 20, 24, 14, 20, 24, 27,
	  20, 24, 27, 30, 24, 27, 30, 34 }
};

static const uint8_t default_scaling8[2][64] = {
	{  6, 10, 13, 16, 18, 23, 25, 27,
	  10, 11, 16, 18, 23, 25, 27, 29,
	  13, 16, 18, 23, 25, 27, 29, 31,
	  16, 18, 23, 25, 27, 29, 31, 33,
	  18, 23, 25, 27, 29, 31, 33, 36,
	  23, 25, 27, 29, 31, 33, 36, 38,
	  25, 27, 29, 31, 33, 36, 38, 40,
	  27, 29, 31, 33, 36, 38, 40, 42 },
	{  9, 13, 15, 17, 19, 21, 22, 24,
	  13, 13, 17, 19, 21, 22, 24, 25,
	  15, 17, 19, 21, 22, 24, 25, 27,
	  17, 19, 21, 22, 24, 25, 27, 28,
	  19, 21, 22, 24, 25, 27, 28, 30,
	  21, 22, 24, 25, 27, 28, 30, 32,
	  22, 24, 25, 27, 28, 30, 32, 33,
	  24, 25, 27, 28, 30, 32, 33, 35 }
};

static int decode_scaling_list(struct bitstream *gb, uint8_t *factors, int size,
                               const uint8_t *jvt_list, const uint8_t *fallback_list,
                               uint16_t *mask, int pos)
{
	int i, last = 8, next = 8;
	const uint8_t *scan = size == 16 ? h264_avd_zigzag_scan4x4 : h264_avd_zigzag_scan8x8;
	uint16_t seq_scaling_list_present_flag = get_bits1(gb);
	*mask |= (seq_scaling_list_present_flag << pos);
	if (!seq_scaling_list_present_flag) /* matrix not written, we use the predicted one */
		memcpy(factors, fallback_list, size * sizeof(uint8_t));
	else
		for (i = 0; i < size; i++) {
			if (next) {
				int32_t delta_scale = get_se_golomb(gb);
				if (delta_scale < -128 || delta_scale > 127) {
					h264_err("delta scale %d is invalid\n", delta_scale);
					return -EINVALDATA;
				}
				next = (last + delta_scale + 256) % 256;
			}
			if (!i && !next) { /* matrix not written, we use the preset one */
				memcpy(factors, jvt_list, size * sizeof(uint8_t));
				break;
			}
			last = factors[scan[i]] = next ? next : last;
		}
	return 0;
}

/* returns non zero if the provided SPS scaling matrix has been filled */
static int h264_parse_scaling_list(struct bitstream *gb, struct h264_sps *sps,
                                    struct h264_pps *pps, int is_sps,
                                    int present_flag, uint16_t *mask,
                                    uint8_t(*scaling_matrix4)[16],
                                    uint8_t(*scaling_matrix8)[64])
{
	int fallback_sps = !is_sps && sps->seq_scaling_matrix_present_flag;
	const uint8_t *fallback[4] = {
		fallback_sps ? sps->seq_scaling_list_4x4[0] : default_scaling4[0],
		fallback_sps ? sps->seq_scaling_list_4x4[3] : default_scaling4[1],
		fallback_sps ? sps->seq_scaling_list_8x8[0] : default_scaling8[0],
		fallback_sps ? sps->seq_scaling_list_8x8[3] : default_scaling8[1]
	};
	int ret = 0;
	*mask = 0x0;
	if (present_flag) {
		ret |= decode_scaling_list(gb, scaling_matrix4[0], 16, default_scaling4[0], fallback[0], mask, 0);        // Intra, Y
		ret |= decode_scaling_list(gb, scaling_matrix4[1], 16, default_scaling4[0], scaling_matrix4[0], mask, 1); // Intra, Cr
		ret |= decode_scaling_list(gb, scaling_matrix4[2], 16, default_scaling4[0], scaling_matrix4[1], mask, 2); // Intra, Cb
		ret |= decode_scaling_list(gb, scaling_matrix4[3], 16, default_scaling4[1], fallback[1], mask, 3);        // Inter, Y
		ret |= decode_scaling_list(gb, scaling_matrix4[4], 16, default_scaling4[1], scaling_matrix4[3], mask, 4); // Inter, Cr
		ret |= decode_scaling_list(gb, scaling_matrix4[5], 16, default_scaling4[1], scaling_matrix4[4], mask, 5); // Inter, Cb
		if (is_sps || pps->transform_8x8_mode_flag) {
			ret |= decode_scaling_list(gb, scaling_matrix8[0], 64, default_scaling8[0], fallback[2], mask, 6); // Intra, Y
			ret |= decode_scaling_list(gb, scaling_matrix8[3], 64, default_scaling8[1], fallback[3], mask, 6+3); // Inter, Y
			if (sps->chroma_format_idc == 3) {
				ret |= decode_scaling_list(gb, scaling_matrix8[1], 64, default_scaling8[0], scaling_matrix8[0], mask,  6+1); // Intra, Cr
				ret |= decode_scaling_list(gb, scaling_matrix8[4], 64, default_scaling8[1], scaling_matrix8[3], mask,  6+4); // Inter, Cr
				ret |= decode_scaling_list(gb, scaling_matrix8[2], 64, default_scaling8[0], scaling_matrix8[1], mask,  6+2); // Intra, Cb
				ret |= decode_scaling_list(gb, scaling_matrix8[5], 64, default_scaling8[1], scaling_matrix8[4], mask,  6+5); // Inter, Cb
			}
		}
		if (!ret)
			ret = is_sps;
	}

	return ret;
}

static int h264_parse_hrd_parameters(struct bitstream *gb, struct h264_hrd_parameters *hrd)
{
	int i;

	hrd->cpb_cnt = get_ue_golomb_31(gb) + 1;
	if (hrd->cpb_cnt >= 32) {
		h264_err("cpb_cnt (%d) out of bounds\n", hrd->cpb_cnt);
		return -1;
	}

	hrd->bit_rate_scale = get_bits(gb, 4);
	hrd->cpb_size_scale = get_bits(gb, 4);

	for (i = 0; i < hrd->cpb_cnt; i++) {
		hrd->bit_rate_value[i] = get_ue_golomb_long(gb) + 1;
		hrd->cpb_size_value[i] = get_ue_golomb_long(gb) + 1;
		hrd->cbr_flag[i]       = get_bits1(gb);
	}

	hrd->initial_cpb_removal_delay_length = get_bits(gb, 5) + 1;
	hrd->cpb_removal_delay_length         = get_bits(gb, 5) + 1;
	hrd->dpb_output_delay_length          = get_bits(gb, 5) + 1;
	hrd->time_offset_length               = get_bits(gb, 5);

	return 0;
}

static int h264_parse_vui_parameters(struct bitstream *gb, struct h264_vui *vui)
{
	vui->aspect_ratio_idc = 0;
	vui->sar_width = 0;

	vui->aspect_ratio_info_present_flag = get_bits1(gb);
	if (vui->aspect_ratio_info_present_flag) {
		vui->aspect_ratio_idc = get_bits(gb, 8);
		if (vui->aspect_ratio_idc == 255) { /* extended SAR */
			vui->sar_width  = get_bits(gb, 16);
			vui->sar_height = get_bits(gb, 16);
		} else {
			if (vui->aspect_ratio_idc < ARRAY_SIZE(h2645_pixel_aspect_ratios)) {
				vui->sar_width = h2645_pixel_aspect_ratios[vui->aspect_ratio_idc][1];
			} else {
				h264_err("WARNING: unknown aspect_ratio_idc %d\n",
					vui->aspect_ratio_idc);
			}
		}
	}

	vui->overscan_info_present_flag = get_bits1(gb);
	if (vui->overscan_info_present_flag)
		vui->overscan_appropriate_flag = get_bits1(gb);

	vui->video_format = 5;
	vui->video_full_range_flag = 0;
	vui->colour_description_present_flag = 0;

	vui->colour_primaries = 2;
	vui->transfer_characteristics = 2;
	vui->matrix_coefficients = 2;

	vui->video_signal_type_present_flag = get_bits1(gb);
	if (vui->video_signal_type_present_flag) {
		vui->video_format                    = get_bits(gb, 3);
		vui->video_full_range_flag           = get_bits1(gb);
		vui->colour_description_present_flag = get_bits1(gb);
		if (vui->colour_description_present_flag) {
			vui->colour_primaries         = get_bits(gb, 8);
			vui->transfer_characteristics = get_bits(gb, 8);
			vui->matrix_coefficients      = get_bits(gb, 8);
		}
	}

	vui->chroma_sample_loc_type_top_field = 0;
	vui->chroma_sample_loc_type_bottom_field = 0;
	vui->chroma_loc_info_present_flag = get_bits1(gb);
	if (vui->chroma_loc_info_present_flag) {
		vui->chroma_sample_loc_type_top_field    = get_ue_golomb_31(gb);
		vui->chroma_sample_loc_type_bottom_field = get_ue_golomb_31(gb);
	}

	vui->fixed_frame_rate_flag = 0;
	vui->timing_info_present_flag = get_bits1(gb);
	if (vui->timing_info_present_flag) {
		vui->num_units_in_tick     = get_bits(gb, 32);
		vui->time_scale            = get_bits(gb, 32);
		vui->fixed_frame_rate_flag = get_bits1(gb);
	}

	vui->nal_hrd_parameters_flag = get_bits1(gb);
	if (vui->nal_hrd_parameters_flag) {
		if (h264_parse_hrd_parameters(gb, &vui->nal_hrd_parameters))
			return -1;
	}

	vui->vcl_hrd_parameters_flag = get_bits1(gb);
	if (vui->vcl_hrd_parameters_flag) {
		if (h264_parse_hrd_parameters(gb, &vui->vcl_hrd_parameters))
			return -1;
	}
	if (vui->vcl_hrd_parameters_flag || vui->nal_hrd_parameters_flag) {
		vui->low_delay_hrd_flag = get_bits1(gb);
	}

	vui->pic_struct_present_flag = get_bits1(gb);
	vui->bitstream_restriction_present_flag = get_bits1(gb);
	if (vui->bitstream_restriction_present_flag) {
		vui->motion_vectors_over_pic_bounduaries_flag = get_bits1(gb);
		vui->max_bytes_per_pic_denom = get_ue_golomb_31(gb);
		vui->max_bits_per_mb_denom = get_ue_golomb_31(gb);
		vui->log2_max_mv_length_horizontal = get_ue_golomb_31(gb);
		vui->log2_max_mv_length_vertical = get_ue_golomb_31(gb);
		vui->num_reorder_frames = get_ue_golomb_31(gb);
		vui->max_dec_frame_buffering = get_ue_golomb_31(gb);
	} else {
		vui->motion_vectors_over_pic_bounduaries_flag = 1;
		vui->max_bytes_per_pic_denom = 2;
		vui->max_bits_per_mb_denom = 1;
		vui->log2_max_mv_length_horizontal = 16;
		vui->log2_max_mv_length_vertical = 16;
		/* XXX: not entirely correct */
		vui->num_reorder_frames = 16;
		vui->max_dec_frame_buffering = 16;
	}

	return 0;
}

static int h264_parse_sps(struct bitstream *gb, struct h264_sps *sps)
{
	uint32_t i, constraint_set_flags = 0;
	int ret;

	sps->is_svc = 0;
	sps->is_mvc = 0;

	sps->profile_idc      = get_bits(gb, 8);
	constraint_set_flags |= get_bits1(gb) << 0;   // constraint_set0_flag
	constraint_set_flags |= get_bits1(gb) << 1;   // constraint_set1_flag
	constraint_set_flags |= get_bits1(gb) << 2;   // constraint_set2_flag
	constraint_set_flags |= get_bits1(gb) << 3;   // constraint_set3_flag
	constraint_set_flags |= get_bits1(gb) << 4;   // constraint_set4_flag
	constraint_set_flags |= get_bits1(gb) << 5;   // constraint_set5_flag
	skip_bits(gb, 2);                             // reserved_zero_2bits

	sps->level_idc            = get_bits(gb, 8);
	sps->seq_parameter_set_id = get_ue_golomb_31(gb);
	if (sps->seq_parameter_set_id >= H264_MAX_SPS_COUNT) {
		h264_err("SPS id %u out of range\n", sps->seq_parameter_set_id);
		return -1;
	}

	sps->seq_scaling_matrix_present_flag = 0;
	memset(sps->seq_scaling_list_4x4, 16, sizeof(sps->seq_scaling_list_4x4));
	memset(sps->seq_scaling_list_8x8, 16, sizeof(sps->seq_scaling_list_8x8));

	switch (sps->profile_idc) {
	case H264_PROFILE_BASELINE:
	case H264_PROFILE_MAIN:
	case H264_PROFILE_EXTENDED:
		sps->chroma_format_idc = 1;
		sps->separate_colour_plane_flag = 0;
		sps->bit_depth_luma_minus8 = 0;
		sps->bit_depth_chroma_minus8 = 0;
		sps->qpprime_y_zero_transform_bypass_flag = 0;
		sps->seq_scaling_matrix_present_flag = 0;
		break;
	case H264_PROFILE_HIGH:
	case H264_PROFILE_HIGH_10:
	case H264_PROFILE_HIGH_422:
	case H264_PROFILE_HIGH_444_PRED:
	case H264_PROFILE_CAVLC_444:
	case H264_PROFILE_SCALABLE_BASELINE:
	case H264_PROFILE_SCALABLE_HIGH:
	case H264_PROFILE_MULTIVIEW_HIGH:
	case H264_PROFILE_STEREO_HIGH:
		sps->chroma_format_idc = get_ue_golomb_31(gb);
		sps->separate_colour_plane_flag = 0;
		if (sps->chroma_format_idc == 3)
			sps->separate_colour_plane_flag = get_bits1(gb);

		sps->bit_depth_luma_minus8 = get_ue_golomb_31(gb);
		sps->bit_depth_chroma_minus8 = get_ue_golomb_31(gb);
		sps->qpprime_y_zero_transform_bypass_flag = get_bits1(gb);
		sps->seq_scaling_matrix_present_flag = get_bits1(gb);
		ret = h264_parse_scaling_list(gb, sps, NULL, 1, sps->seq_scaling_matrix_present_flag,
									  &sps->scaling_matrix_present_mask,
									  sps->seq_scaling_list_4x4, sps->seq_scaling_list_8x8);
		if (ret < 0)
			h264_err("failed to decode scaling list (%d)\n", ret);
		sps->seq_scaling_matrix_present_flag |= ret;
		break;
	default:
		h264_err("unknown profile (%d)\n", sps->profile_idc);
		return -1;
	}

	sps->log2_max_frame_num = get_ue_golomb_31(gb) + 4;
	sps->pic_order_cnt_type = get_ue_golomb_31(gb);
	switch (sps->pic_order_cnt_type) {
	case 0:
		sps->log2_max_pic_order_cnt_lsb       = get_ue_golomb_31(gb) + 4;
		break;
	case 1:
		sps->delta_pic_order_always_zero_flag = get_bits1(gb);
	        sps->offset_for_non_ref_pic           = get_se_golomb_long(gb);
	        sps->offset_for_top_to_bottom_field   = get_se_golomb_long(gb);
		sps->num_ref_frames_in_pic_order_cnt_cycle = get_ue_golomb(gb);

		for (i = 0; i < sps->num_ref_frames_in_pic_order_cnt_cycle; i++) {
			sps->offset_for_ref_frame[i] = get_se_golomb_long(gb);
		}
		break;
	}

	sps->max_num_ref_frames                   = get_ue_golomb_31(gb);
	sps->gaps_in_frame_num_value_allowed_flag = get_bits1(gb);
	sps->pic_width_in_mbs                     = get_ue_golomb(gb) + 1;
	sps->pic_height_in_map_units              = get_ue_golomb(gb) + 1;

	sps->frame_mbs_only_flag = get_bits1(gb);
	if (!sps->frame_mbs_only_flag) {
		sps->mb_adaptive_frame_field_flag = get_bits1(gb);
	} else {
		sps->mb_adaptive_frame_field_flag = 0;
	}

	sps->direct_8x8_inference_flag = get_bits1(gb);
	sps->frame_cropping_flag = get_bits1(gb);
	if (sps->frame_cropping_flag) {
		sps->frame_crop_left_offset   = get_ue_golomb(gb);
		sps->frame_crop_right_offset  = get_ue_golomb(gb);
		sps->frame_crop_top_offset    = get_ue_golomb(gb);
		sps->frame_crop_bottom_offset = get_ue_golomb(gb);
	} else {
		sps->frame_crop_left_offset   = 0;
		sps->frame_crop_right_offset  = 0;
		sps->frame_crop_top_offset    = 0;
		sps->frame_crop_bottom_offset = 0;
	}

	sps->vui_parameters_present_flag = get_bits1(gb);
	if (sps->vui_parameters_present_flag)
		if (h264_parse_vui_parameters(gb, &sps->vui))
			return -1;

	return 0;
}

static int h264_svc_vui_parameters(struct bitstream *gb, struct h264_vui *vui)
{
	(void)gb;
	(void)vui;
	h264_err("patch welcome\n");
	return -1;
}

static int h264_parse_sps_svc(struct bitstream *gb, struct h264_sps *sps)
{
	sps->is_svc = 1;

	sps->inter_layer_deblocking_filter_control_present_flag = get_bits1(gb);
	sps->extended_spatial_scalability_idc = get_bits(gb, 2);

	sps->chroma_phase_x_plus1_flag = 1;
	if (sps->chroma_format_idc == 1 || sps->chroma_format_idc == 2)
		sps->chroma_phase_x_plus1_flag = get_bits1(gb);

	sps->chroma_phase_y_plus1 = 1;
	if (sps->chroma_format_idc == 1)
		sps->chroma_phase_y_plus1 = get_bits(gb, 2);

	if (sps->extended_spatial_scalability_idc == 1) {
		if (sps->chroma_format_idc && !sps->separate_colour_plane_flag) {
			sps->seq_ref_layer_chroma_phase_x_plus1_flag = get_bits1(gb);
			sps->seq_ref_layer_chroma_phase_y_plus1      = get_bits(gb, 2);
		} else {
			sps->seq_ref_layer_chroma_phase_x_plus1_flag = 1;
			sps->seq_ref_layer_chroma_phase_y_plus1      = 1;
		}
		sps->seq_ref_layer_left_offset   = bs_read_se(gb);
		sps->seq_ref_layer_top_offset    = bs_read_se(gb);
		sps->seq_ref_layer_right_offset  = bs_read_se(gb);
		sps->seq_ref_layer_bottom_offset = bs_read_se(gb);
	} else {
		sps->seq_ref_layer_chroma_phase_x_plus1_flag = sps->chroma_phase_x_plus1_flag;
		sps->seq_ref_layer_chroma_phase_y_plus1 = sps->chroma_phase_y_plus1;
		sps->seq_ref_layer_left_offset   = 0;
		sps->seq_ref_layer_top_offset    = 0;
		sps->seq_ref_layer_right_offset  = 0;
		sps->seq_ref_layer_bottom_offset = 0;
	}

	sps->seq_tcoeff_level_prediction_flag              = get_bits1(gb);
	sps->adaptive_tcoeff_level_prediction_flag         = 0;
	if (sps->seq_tcoeff_level_prediction_flag)
		sps->adaptive_tcoeff_level_prediction_flag = get_bits1(gb);

	sps->slice_header_restriction_flag   = get_bits1(gb);
	sps->svc_vui_parameters_present_flag = get_bits1(gb);
	if (sps->svc_vui_parameters_present_flag)
		if (h264_svc_vui_parameters(gb, &sps->svc_vui))
			return -1;
	return 0;
}

static int h264_mvc_vui_parameters(struct bitstream *gb, struct h264_vui *vui)
{
	(void)gb;
	(void)vui;
	h264_err("patch welcome\n");
	return -1;
}

static int h264_parse_sps_mvc(struct bitstream *gb, struct h264_sps *sps)
{
	uint32_t i = 0, j = 0, k;
	int err = 0;

	sps->is_mvc = 1;
	if (!get_bits1(gb)) {
		h264_err("SPS MVC marker bit not set\n");
		return -1;
	}

	sps->num_views = bs_read_ue(gb) + 1;
	sps->views = calloc(sizeof *sps->views, sps->num_views);
	if (!sps->views) {
		err = -1;
		goto exit;
	}

	for (i = 0; i < sps->num_views; i++)
		sps->views[i].view_id = bs_read_ue(gb);
	for (i = 1; i < sps->num_views; i++) {
		sps->views[i].num_anchor_refs_l0 = bs_read_ue(gb);
		if (sps->views[i].num_anchor_refs_l0 > 15) {
			h264_err("num_anchor_refs_l0 over limit\n");
			err = -1;
			goto free_views;
		}

		for (j = 0; j < sps->views[i].num_anchor_refs_l0; j++)
			sps->views[i].anchor_ref_l0[j] = bs_read_ue(gb);

		sps->views[i].num_anchor_refs_l1 = bs_read_ue(gb);
		if (sps->views[i].num_anchor_refs_l1 > 15) {
			h264_err("num_anchor_refs_l1 over limit\n");
			err = -1;
			goto free_views;
		}

		for (j = 0; j < sps->views[i].num_anchor_refs_l1; j++)
			sps->views[i].anchor_ref_l1[j] = bs_read_ue(gb);
	}

	for (i = 1; i < sps->num_views; i++) {
		sps->views[i].num_non_anchor_refs_l0 = bs_read_ue(gb);
		if (sps->views[i].num_non_anchor_refs_l0 > 15) {
			h264_err("num_non_anchor_refs_l0 over limit\n");
			err = -1;
			goto free_views;
		}
		for (j = 0; j < sps->views[i].num_non_anchor_refs_l0; j++)
			sps->views[i].non_anchor_ref_l0[j] = bs_read_ue(gb);

		sps->views[i].num_non_anchor_refs_l1 = bs_read_ue(gb);
		if (sps->views[i].num_non_anchor_refs_l1 > 15) {
			h264_err("num_non_anchor_refs_l1 over limit\n");
			err = -1;
			goto free_views;
		}
		for (j = 0; j < sps->views[i].num_non_anchor_refs_l1; j++)
			sps->views[i].non_anchor_ref_l1[j] = bs_read_ue(gb);
	}

	sps->num_level_values_signalled = bs_read_ue(gb);
	sps->levels = calloc(sizeof *sps->levels, sps->num_level_values_signalled);
	if (!sps->levels) {
		err = -1;
		goto free_views;
	}

	for (i = 0; i < sps->num_level_values_signalled; i++) {
		sps->levels[i].level_idc = get_bits(gb, 8);
		sps->levels[i].num_applicable_ops = bs_read_ue(gb) + 1;
		sps->levels[i].applicable_ops =
				calloc(sizeof *sps->levels[i].applicable_ops,
				       sps->levels[i].num_applicable_ops);
		if (!sps->levels[i].applicable_ops) {
			err = -1;
			goto free_levels;
		}

		for (j = 0; j < sps->levels[i].num_applicable_ops; j++) {
			sps->levels[i].applicable_ops[j].temporal_id = get_bits(gb, 3);
			sps->levels[i].applicable_ops[j].num_target_views = bs_read_ue(gb) + 1;
			sps->levels[i].applicable_ops[j].target_view_id =
					calloc(sizeof *sps->levels[i].applicable_ops[j].target_view_id,
					       sps->levels[i].applicable_ops[j].num_target_views);
			if (!sps->levels[i].applicable_ops[j].target_view_id) {
				err = -1;
				goto free_levels;
			}

			for (k = 0; k <= sps->levels[i].applicable_ops[j].num_target_views; k++)
				sps->levels[i].applicable_ops[j].target_view_id[k] = bs_read_ue(gb);
			sps->levels[i].applicable_ops[j].num_views = bs_read_ue(gb) + 1;
		}
	}

	sps->mvc_vui_parameters_present_flag = get_bits1(gb);
	if (sps->mvc_vui_parameters_present_flag) {
		err = h264_mvc_vui_parameters(gb, &sps->mvc_vui);
		if (err < 0)
			goto free_levels;
	}

free_levels:
	while (i--) {
		free(sps->levels[i].applicable_ops);
		while (j--)
			free(sps->levels[i].applicable_ops[j].target_view_id);
	}
	free(sps->levels);
free_views:
	free(sps->views);
exit:
	return err;
}

static int h264_parse_sps_ext(struct h264_context *ctx, uint32_t *pseq_parameter_set_id)
{
	struct bitstream *gb = &ctx->gb;

	uint32_t ps_id = bs_read_ue(gb);
	if (ps_id > 31) {
		h264_err("PSEQ id (%d) out of bounds\n", ps_id);
		return -1;
	}
	*pseq_parameter_set_id = ps_id;

	struct h264_sps *sps = &ctx->sps_list[ps_id];
	sps->has_ext = 1;
	sps->aux_format_idc = bs_read_ue(gb);
	if (sps->aux_format_idc) {
		sps->bit_depth_aux_minus8    = bs_read_ue(gb);
		sps->alpha_incr_flag         = get_bits1(gb);
		sps->alpha_opaque_value      = get_bits(gb, sps->bit_depth_aux_minus8 + 9);
		sps->alpha_transparent_value = get_bits(gb, sps->bit_depth_aux_minus8 + 9);
	}

	if (get_bits1(gb)) {
		h264_err("WARNING: additional data in SPS extension\n");
		while (h2645_more_rbsp_data(gb))
			get_bits1(gb);
	}

	return 0;
}

static int h264_parse_pps(struct h264_context *ctx, struct h264_pps *pps)
{
	struct bitstream *gb = &ctx->gb;
	struct h264_sps *sps = NULL;
	int i, ret;

	pps->pic_parameter_set_id = get_ue_golomb(gb);
	pps->seq_parameter_set_id = get_ue_golomb_31(gb);
	if (pps->seq_parameter_set_id >= H264_MAX_SPS_COUNT) {
		h264_err("SPS id (%d) out of bounds\n", pps->seq_parameter_set_id);
		return -1;
	}
	sps = &ctx->sps_list[pps->seq_parameter_set_id];
	pps->chroma_format_idc = sps->chroma_format_idc;

	pps->entropy_coding_mode_flag = get_bits1(gb);
	pps->bottom_field_pic_order_in_frame_present_flag = get_bits1(gb);
	pps->num_slice_groups = get_ue_golomb(gb) + 1;
	if (pps->num_slice_groups > 1) {
		if (pps->num_slice_groups > 7) {
			h264_err("num_slice_groups over limit\n");
			return -1;
		}
		pps->slice_group_map_type = get_ue_golomb(gb);
		switch (pps->slice_group_map_type) {
		case H264_SLICE_GROUP_MAP_INTERLEAVED:
			for (i = 0; i < pps->num_slice_groups; i++)
				pps->run_length[i]   = get_ue_golomb(gb) + 1;
			break;
		case H264_SLICE_GROUP_MAP_DISPERSED:
			break;
		case H264_SLICE_GROUP_MAP_FOREGROUND:
			for (i = 0; i < pps->num_slice_groups; i++) {
				pps->top_left[i]     = bs_read_ue(gb);
				pps->bottom_right[i] = bs_read_ue(gb);
			}
			break;
		case H264_SLICE_GROUP_MAP_CHANGING_BOX:
		case H264_SLICE_GROUP_MAP_CHANGING_VERTICAL:
		case H264_SLICE_GROUP_MAP_CHANGING_HORIZONTAL:
			pps->slice_group_change_direction_flag = get_bits1(gb);
			pps->slice_group_change_rate           = bs_read_ue(gb) + 1;
			break;
		case H264_SLICE_GROUP_MAP_EXPLICIT:
			pps->pic_size_in_map_units = bs_read_ue(gb) + 1;
			static const int id_sizes[8] = { 0, 1, 2, 2, 3, 3, 3, 3 };
			for (i = 0; i < pps->pic_size_in_map_units; i++)
				get_bits(gb, id_sizes[pps->num_slice_groups]); /* slice_group_id */
			break;
		default:
			h264_err("unknown slice_group_map_type %d!\n",
				pps->slice_group_map_type);
			return -1;
		}
	}

	pps->num_ref_idx_l0_default_active = get_ue_golomb(gb) + 1;
	pps->num_ref_idx_l1_default_active = get_ue_golomb(gb) + 1;

	pps->weighted_pred_flag  = get_bits1(gb);
	pps->weighted_bipred_idc = get_bits(gb, 2);
	pps->pic_init_qp_minus26 = get_se_golomb(gb);
	pps->pic_init_qs_minus26 = get_se_golomb(gb);
	pps->chroma_qp_index_offset = get_se_golomb(gb);

	pps->deblocking_filter_control_present_flag = get_bits1(gb);
	pps->constrained_intra_pred_flag = get_bits1(gb);
	pps->redundant_pic_cnt_present_flag = get_bits1(gb);

	memcpy(pps->pic_scaling_list_4x4, sps->seq_scaling_list_4x4,
		   sizeof(pps->pic_scaling_list_4x4));
	memcpy(pps->pic_scaling_list_8x8, sps->seq_scaling_list_8x8,
		   sizeof(pps->pic_scaling_list_8x8));
	if (h2645_more_rbsp_data(gb)) {
		pps->transform_8x8_mode_flag = get_bits1(gb);
		pps->pic_scaling_matrix_present_flag = get_bits1(gb);
		ret = h264_parse_scaling_list(gb, sps, pps, 0,
								pps->pic_scaling_matrix_present_flag,
								&pps->pic_scaling_matrix_present_mask,
								pps->pic_scaling_list_4x4, pps->pic_scaling_list_8x8);
		if (ret < 0) {
			h264_err("failed to parse scaling list\n");
		}
		pps->second_chroma_qp_index_offset = get_se_golomb(gb);
	} else {
		pps->transform_8x8_mode_flag = 0;
		pps->pic_scaling_matrix_present_flag = 0;
		pps->second_chroma_qp_index_offset = pps->chroma_qp_index_offset;
	}

	return 0;
}

static int h264_parse_ref_pic_list_modification(struct bitstream *gb,
					  struct h264_ref_pic_list_modification *list)
{
	list->flag = get_bits1(gb);
	if (list->flag) {
		int i = 0;
		do {
			list->list[i].op = get_ue_golomb_31(gb);
			if (list->list[i].op != 3) {
				list->list[i].param = get_ue_golomb_long(gb);
				if (i == 32) {
					h264_err("too many ref_pic_list_modification entries\n");
					return 1;
				}
			}
		} while (list->list[i++].op != 3);
	} else {
		list->list[0].op = 3;
	}

	return 0;
}

static int h264_parse_dec_ref_pic_marking(struct bitstream *gb, struct h264_slice *sl)
{
	int i = 0;

	sl->num_mmcos = 0;
	sl->no_output_of_prior_pics_flag = 0;
	sl->long_term_reference_flag = 0;
	sl->adaptive_ref_pic_marking_mode_flag = 0;

	if (sl->nal_unit_type == H264_NAL_SLICE_IDR) {
		sl->no_output_of_prior_pics_flag = get_bits1(gb);
		sl->long_term_reference_flag = get_bits1(gb);
	} else {
		sl->adaptive_ref_pic_marking_mode_flag = get_bits1(gb);
		if (sl->adaptive_ref_pic_marking_mode_flag) {
			for (i = 0; i < H264_MAX_MMCO_COUNT; i++) {
				struct h264_mmco *mmco = &sl->mmcos[i];
				mmco->opcode = get_ue_golomb_31(gb);

				if (mmco->opcode == H264_MMCO_FORGET_SHORT ||
				    mmco->opcode == H264_MMCO_SHORT_TO_LONG) {
					mmco->short_pic_num = get_ue_golomb_long(gb);
				}

				if (mmco->opcode == H264_MMCO_SHORT_TO_LONG ||
				    mmco->opcode == H264_MMCO_FORGET_LONG ||
				    mmco->opcode == H264_MMCO_THIS_TO_LONG ||
				    mmco->opcode == H264_MMCO_FORGET_LONG_MAX) {
					mmco->long_arg = get_ue_golomb_31(gb);
				}

				if (mmco->opcode > (unsigned)H264_MMCO_THIS_TO_LONG) {
					h264_err("illegal mmco opcode %d\n", mmco->opcode);
					return -1;
				}
				if (mmco->opcode == H264_MMCO_END)
					break;
			}
		}
	}

	sl->num_mmcos = i;

	return 0;
}

static int h264_parse_dec_ref_base_pic_marking(struct bitstream *gb, struct h264_slice *sl,
					       struct h264_nal_svc_header *svc)
{
	int i = 0;

	sl->num_base_mmcos = 0;

	sl->store_ref_base_pic_flag = get_bits1(gb);
	if ((svc->use_ref_base_pic_flag || sl->store_ref_base_pic_flag) && !svc->idr_flag) {
		sl->adaptive_ref_base_pic_marking_mode_flag = get_bits1(gb);
		if (sl->adaptive_ref_base_pic_marking_mode_flag) {
			for (i = 0; i < H264_MAX_MMCO_COUNT; i++) {
				struct h264_mmco *mmco = &sl->base_mmcos[i];
				mmco->opcode = get_ue_golomb_31(gb);
				switch (mmco->opcode) {
					case H264_MMCO_END:
						break;
					case H264_MMCO_FORGET_SHORT:
						mmco->short_pic_num = get_ue_golomb_long(gb); /* difference_of_pic_nums_minus1 */
						break;
					case H264_MMCO_FORGET_LONG:
						mmco->long_arg = get_ue_golomb_31(gb); /* long_term_pic_num */
						break;
					default:
						h264_err("unknown mmco opcode %d\n", mmco->opcode);
						return -1;
				}
				if (mmco->opcode == H264_MMCO_END) {
					break;
				}
			}
		}
	}

	sl->num_base_mmcos = i;

	return 0;
}

static void h264_pred_weight_table_entry(struct bitstream *gb, struct h264_slice *sl,
					 struct h264_pred_weight_table_entry *entry)
{
	int i;

	entry->luma_weight_flag = get_bits1(gb);
	if (entry->luma_weight_flag) {
		entry->luma_weight = get_se_golomb(gb);
		entry->luma_offset = get_se_golomb(gb);
	} else {
		entry->luma_weight = 1 << sl->luma_log2_weight_denom;
		entry->luma_offset = 0;
	}

	if (sl->has_chroma_weights) {
		entry->chroma_weight_flag = get_bits1(gb);
		if (entry->chroma_weight_flag) {
			for (i = 0; i < 2; i++) {
				entry->chroma_weight[i] = get_se_golomb(gb);
				entry->chroma_offset[i] = get_se_golomb(gb);
			}
		} else {
			for (i = 0; i < 2; i++) {
				entry->chroma_weight[i] = 1 << sl->chroma_log2_weight_denom;
				entry->chroma_offset[i] = 0;
			}
		}
	}
}

static int h264_pred_weight_table(struct h264_context *ctx, struct h264_slice *sl)
{
	struct h264_sps *sps = h264_sl_get_sps(ctx, sl);
	struct bitstream *gb = &ctx->gb;
	uint32_t i;

	sl->has_luma_weights = 1;
	sl->luma_log2_weight_denom = get_ue_golomb_31(gb);
	sl->has_chroma_weights = !sps->separate_colour_plane_flag && sps->chroma_format_idc != 0;
	if (sl->has_chroma_weights)
		sl->chroma_log2_weight_denom = get_ue_golomb_31(gb);

	for (i = 0; i < sl->num_ref_idx_l0_active; i++)
		h264_pred_weight_table_entry(gb, sl, &sl->pwt_l0[i]);

	if (sl->slice_type_nos == H264_SLICE_TYPE_B) {
		for (i = 0; i < sl->num_ref_idx_l1_active; i++)
			h264_pred_weight_table_entry(gb, sl, &sl->pwt_l1[i]);
	}

	return 0;
}

static const uint8_t h264_golomb_to_pict_type[5] = { H264_SLICE_TYPE_P, H264_SLICE_TYPE_B,
						     H264_SLICE_TYPE_I,
						     H264_SLICE_TYPE_SP,
						     H264_SLICE_TYPE_SI };

static int h264_parse_slice_header(struct h264_context *ctx, struct h264_slice *sl)
{
	struct bitstream *gb = &ctx->gb;
	struct h264_sps *sps = NULL;
	struct h264_pps *pps = NULL;
	uint32_t slice_type;

	sl->first_mb_in_slice = get_ue_golomb_long(gb);

	slice_type = get_ue_golomb_31(gb);
	if (slice_type > 9) {
		h264_err("slice type %d too large at %d\n", slice_type,
		       sl->first_mb_in_slice);
		return -1;
	}

	if (slice_type > 4) {
		slice_type -= 5;
		sl->slice_type_fixed = 1;
	} else {
		sl->slice_type_fixed = 0;
	}

	slice_type = h264_golomb_to_pict_type[slice_type];
	sl->slice_type     = slice_type;
	sl->slice_type_nos = slice_type & 3;

	sl->pic_parameter_set_id = get_ue_golomb(gb);
	if (sl->pic_parameter_set_id >= H264_MAX_PPS_COUNT) {
		h264_err("pic_parameter_set_id out of range\n");
		return -1;
	}

	pps = h264_get_pps(ctx, sl->pic_parameter_set_id);
	if (!pps) {
		h264_err("PPS id (%d) points to NULL PPS\n",
			sl->pic_parameter_set_id);
		return -1;
	}

	sps = h264_get_sps(ctx, sl->pic_parameter_set_id);
	if (!sps) {
		h264_err("SPS id (%d) points to NULL SPS\n",
			pps->seq_parameter_set_id);
		return -1;
	}

	if (sl->nal_unit_type == H264_NAL_SLICE_AUX) {
		sl->chroma_array_type = 0;
		sl->bit_depth_luma_minus8 = sps->bit_depth_aux_minus8;
		sl->bit_depth_chroma_minus8 = 0;
	} else {
		sl->chroma_array_type =
			(sps->separate_colour_plane_flag ? 0 : sps->chroma_format_idc);
		sl->bit_depth_luma_minus8 = sps->bit_depth_luma_minus8;
		sl->bit_depth_chroma_minus8 = sps->bit_depth_chroma_minus8;
	}

	if (sps->separate_colour_plane_flag)
		sl->colour_plane_id = get_bits(gb, 2);

	sl->frame_num = get_bits(gb, sps->log2_max_frame_num);

	sl->field_pic_flag = 0;
	sl->bottom_field_flag = 0;

	if (sps->frame_mbs_only_flag) {
	        sl->picture_structure = PICT_FRAME;
	}
	else {
		sl->field_pic_flag = get_bits1(gb);
		if (sl->field_pic_flag) {
			sl->bottom_field_flag = get_bits1(gb);
			sl->picture_structure = PICT_TOP_FIELD + sl->bottom_field_flag;
		} else {
	            sl->picture_structure = PICT_FRAME;
	        }
	}

	if (sl->nal_unit_type == H264_NAL_SLICE_IDR) {
		sl->idr_pic_id = get_ue_golomb_long(gb);
		if (sl->idr_pic_id >= 65536) {
			h264_err("idr_pic_id (%d) out of bounds\n", sl->idr_pic_id);
			return -1;
		}
	}

	sl->width = (sps->pic_width_in_mbs * 16) - (sps->frame_crop_right_offset * 2) - (sps->frame_crop_left_offset * 2);
	sl->height = ((2 - sps->frame_mbs_only_flag) * sps->pic_height_in_map_units * 16) - (sps->frame_crop_bottom_offset * 2) - (sps->frame_crop_top_offset * 2);
	sl->width_mbs = sps->pic_width_in_mbs;
	sl->height_mbs = sps->pic_height_in_map_units;
	if (!sps->frame_mbs_only_flag)
		sl->height_mbs *= 2;
	if (sl->field_pic_flag)
		sl->height_mbs /= 2;
	sl->pic_size_in_mbs = sl->width_mbs * sl->height_mbs;
	sl->mbaff_frame_flag = sps->mb_adaptive_frame_field_flag && !sl->field_pic_flag;

	switch (sps->pic_order_cnt_type) {
	case 0:
		sl->pic_order_cnt_lsb = get_bits(gb, sps->log2_max_pic_order_cnt_lsb);
		sl->delta_pic_order_cnt_bottom = 0;
		if (pps->bottom_field_pic_order_in_frame_present_flag &&
		    !sl->field_pic_flag) {
			sl->delta_pic_order_cnt_bottom = get_se_golomb(gb);
		}
		break;
	case 1:
		sl->delta_pic_order_cnt[0] = 0;
		sl->delta_pic_order_cnt[1] = 0;
		if (!sps->delta_pic_order_always_zero_flag) {
			sl->delta_pic_order_cnt[0] = get_se_golomb(gb);
			if (pps->bottom_field_pic_order_in_frame_present_flag &&
			    !sl->field_pic_flag) {
				sl->delta_pic_order_cnt[1] = get_se_golomb(gb);
			}
		}
		break;
	}

	sl->redundant_pic_cnt = 0;
	if (pps->redundant_pic_cnt_present_flag)
		sl->redundant_pic_cnt = get_ue_golomb(gb);

	sl->has_luma_weights = 0;
	sl->has_chroma_weights = 0;

	if (!sps->is_svc || sl->svc.quality_id == 0) {
		if (sl->slice_type == H264_SLICE_TYPE_B)
			sl->direct_spatial_mb_pred_flag = get_bits1(gb);
		if (sl->slice_type_nos != H264_SLICE_TYPE_I) {
			sl->num_ref_idx_active_override_flag = get_bits1(gb);
			if (sl->num_ref_idx_active_override_flag) {
				sl->num_ref_idx_l0_active = get_ue_golomb(gb) + 1;
				if (sl->slice_type_nos == H264_SLICE_TYPE_B)
					sl->num_ref_idx_l1_active = get_ue_golomb(gb) + 1;
			} else {
				sl->num_ref_idx_l0_active = pps->num_ref_idx_l0_default_active;
				if (sl->slice_type_nos == H264_SLICE_TYPE_B) {
					sl->num_ref_idx_l1_active = pps->num_ref_idx_l1_default_active;
				}
			}

			if (sl->num_ref_idx_l0_active >= H264_MAX_REFS) {
				h264_err("num_ref_idx_l0_active (%d) out of bounds\n",
					sl->num_ref_idx_l0_active);
				return -1;
			}
			if (sl->slice_type_nos == H264_SLICE_TYPE_B &&
				sl->num_ref_idx_l1_active >= H264_MAX_REFS) {
				h264_err("num_ref_idx_l1_active (%d) out of bounds\n",
					sl->num_ref_idx_l1_active);
				return -1;
			}
		}

		if (sl->slice_type != H264_SLICE_TYPE_I &&
		    sl->slice_type != H264_SLICE_TYPE_SI) {
			if (h264_parse_ref_pic_list_modification(gb,
				&sl->ref_pic_list_modification_l0))
				return -1;
			if (sl->slice_type == H264_SLICE_TYPE_B) {
				if (h264_parse_ref_pic_list_modification(gb,
					&sl->ref_pic_list_modification_l1))
					return -1;
			}
		}

		if ((pps->weighted_pred_flag && (sl->slice_type == H264_SLICE_TYPE_P || sl->slice_type == H264_SLICE_TYPE_SP)) ||
			(pps->weighted_bipred_idc == 1 && sl->slice_type == H264_SLICE_TYPE_B)) {
			if (h264_pred_weight_table(ctx, sl))
					return -1;
		}

		sl->num_mmcos = 0;
		sl->no_output_of_prior_pics_flag = 0;
		sl->long_term_reference_flag = 0;
		sl->adaptive_ref_pic_marking_mode_flag = 0;
		if (sl->nal_ref_idc) {
			if (h264_parse_dec_ref_pic_marking(gb, sl))
				return -1;
			if (sps->is_svc && !sps->slice_header_restriction_flag) {
				if (h264_parse_dec_ref_base_pic_marking(gb, sl, &sl->svc))
					return -1;
			}
		}
	} else {
		/* XXX: infer me */
	}

	if (pps->entropy_coding_mode_flag && sl->slice_type != H264_SLICE_TYPE_I &&
	    sl->slice_type != H264_SLICE_TYPE_SI) {
		sl->cabac_init_idc = get_ue_golomb_31(gb);
		if (sl->cabac_init_idc > 2) {
			h264_err("cabac_init_idc %u out of range!\n", sl->cabac_init_idc);
			return -1;
		}
	}

	sl->slice_qp_delta = get_se_golomb(gb);
	if (sl->slice_type == H264_SLICE_TYPE_SP)
		sl->sp_for_switch_flag = get_bits1(gb);
	if (sl->slice_type == H264_SLICE_TYPE_SP || sl->slice_type == H264_SLICE_TYPE_SI)
		sl->slice_qs_delta = get_se_golomb(gb);

	sl->disable_deblocking_filter_idc = 0;
	sl->slice_alpha_c0_offset_div2 = 0;
	sl->slice_beta_offset_div2     = 0;
	if (pps->deblocking_filter_control_present_flag) {
		sl->disable_deblocking_filter_idc = get_ue_golomb_31(gb);
		if (sl->disable_deblocking_filter_idc != 1) {
			sl->slice_alpha_c0_offset_div2 = get_se_golomb(gb);
			sl->slice_beta_offset_div2 = get_se_golomb(gb);
			if (sl->slice_alpha_c0_offset_div2 >  6 ||
		                sl->slice_alpha_c0_offset_div2 < -6 ||
		                sl->slice_beta_offset_div2 >  6     ||
		                sl->slice_beta_offset_div2 < -6) {
		                	h264_err("deblocking filter parameters %d %d out of range\n",
			                       sl->slice_alpha_c0_offset_div2, sl->slice_beta_offset_div2);
		                return -1;
			}
		}
	}

	if (pps->num_slice_groups && pps->slice_group_map_type >= 3 &&
	    pps->slice_group_map_type <= 5) {
		size_t s = clog2((sps->pic_width_in_mbs * sps->pic_height_in_map_units)
				/ (pps->slice_group_change_rate + 1));
		sl->slice_group_change_cycle = get_bits(gb, s);
	}

	if (pps->entropy_coding_mode_flag) {
		while (!bs_byte_aligned(gb))
			skip_bits1(gb); /* cabac_alignment_zero_bit */
	}

	return 0;
}

int h264_decode_nal_unit(struct h264_context *ctx, uint8_t *buf, int size)
{
	struct bitstream *gb = NULL;
	uint64_t start_pos, end_pos;
	uint32_t nal_ref_idc;
	uint32_t nal_unit_type;
	int err;

	struct h264_slice *sl = &ctx->slice;
	struct h264_sps sps;
	struct h264_pps pps;
	uint32_t pseq_parameter_set_id;

	int nal_size = size;
	int rbsp_size = size;
	uint8_t *rbsp_buf = (uint8_t *)calloc(1, size);
	if (!rbsp_buf)
		return -1;

	err = h2645_nal_to_rbsp(buf, &nal_size, rbsp_buf, &rbsp_size);
	if (err < 0) {
		h264_err("failed to convert NAL to RBSP\n");
		goto free_rbsp;
	}

	bs_init(&ctx->gb, rbsp_buf, rbsp_size);
	gb = &ctx->gb;
	start_pos = get_bits_pos(gb);
	if (get_bits1(gb) != 0) {
		h264_err("forbidden bit != 0\n");
		goto exit;
	}

	nal_ref_idc = get_bits(gb, 2);
	nal_unit_type = get_bits(gb, 5);
	printf("NAL unit: {\n");
	printf("\tnal_ref_idc = %d\n", nal_ref_idc);
	printf("\tnal_unit_type = %d\n", nal_unit_type);

	switch (nal_unit_type) {
	case H264_NAL_SLICE_NONIDR:
	case H264_NAL_SLICE_IDR:
	case H264_NAL_SLICE_AUX:
		sl->nal_ref_idc = nal_ref_idc;
		sl->nal_unit_type = nal_unit_type;
		if (h264_parse_slice_header(ctx, sl)) {
			h264_err("failed to parse slice header\n");
			goto exit;
		}
		end_pos = get_bits_pos(gb);
		printf("\tslice_header_size = %ld\n", end_pos - start_pos);
		h264_print_slice_header(ctx, sl);
		break;
	case H264_NAL_SEI:
		while (h2645_more_rbsp_data(gb))
			skip_bits1(gb); /* XXX */
		h2645_rbsp_trailing_bits(gb);
		break;
	case H264_NAL_SEQPARM:
		if (h264_parse_sps(gb, &sps)) {
			h264_err("failed to parse sps\n");
			goto exit;
		}
		h2645_rbsp_trailing_bits(gb);
		h264_print_sps(&sps);
		if (sps.seq_parameter_set_id >= H264_MAX_SPS_COUNT) {
			h264_err("SPS id out of bounds\n");
			goto exit;
		}
		memcpy(&ctx->sps_list[sps.seq_parameter_set_id], &sps, sizeof(sps));
		break;
	case H264_NAL_PICPARM:
		if (h264_parse_pps(ctx, &pps)) {
			h264_err("failed to parse pps\n");
			goto exit;
		}
		h2645_rbsp_trailing_bits(gb);
		h264_print_pps(&pps);
		if (pps.pic_parameter_set_id >= H264_MAX_PPS_COUNT) {
			h264_err("PPS id out of bounds\n");
			goto exit;
		}
		memcpy(&ctx->pps_list[pps.pic_parameter_set_id], &pps, sizeof(pps));
		break;
	case H264_NAL_SEQPARM_EXT:

		if (h264_parse_sps_ext(ctx, &pseq_parameter_set_id)) {
			h264_err("failed to parse sps ext\n");
			goto exit;
		}
		h2645_rbsp_trailing_bits(gb);
		h264_print_sps_ext(h264_get_sps(ctx, pseq_parameter_set_id));
		break;
	case H264_NAL_ACC_UNIT_DELIM: {
		int primary_pic_type = get_bits(gb, 3);
		h2645_rbsp_trailing_bits(gb);
		printf("Access unit delimiter:\n");
		static const char *const names[8] = {
			"I",	 "P+I",	 "P+B+I",     "SI",
			"SP+SI", "I+SI", "P+I+SP+SI", "P+B+I+SP+SI",
		};
		printf("\tprimary_pic_type = %d [%s]\n", primary_pic_type,
		       names[primary_pic_type]);
		break;
	}
	case H264_NAL_END_SEQ:
		/* noop */
		h2645_rbsp_trailing_bits(gb);
		break;
	case H264_NAL_END_STREAM:
		/* noop */
		h2645_rbsp_trailing_bits(gb);
		break;
	case H264_NAL_SUBSET_SEQPARM:
		if (h264_parse_sps(gb, &sps)) {
			h264_err("failed to parse SPS\n");
			goto exit;
		}
		switch (sps.profile_idc) {
		case H264_PROFILE_SCALABLE_BASELINE:
		case H264_PROFILE_SCALABLE_HIGH:
			if (h264_parse_sps_svc(gb, &sps)) {
				h264_err("failed to parse SPS SVC\n");
				goto exit;
			}
			break;
		case H264_PROFILE_MULTIVIEW_HIGH:
		case H264_PROFILE_STEREO_HIGH:
			if (h264_parse_sps_mvc(gb, &sps)) {
				h264_err("failed to parse SPS MVC\n");
				goto exit;
			}
			break;
		default:
			break;
		}
		if (get_bits1(gb)) { /* additional_extension_flag */
			h264_err("WARNING: additional data in subset SPS extension\n");
			while (h2645_more_rbsp_data(gb))
				get_bits1(gb);
		}
		h2645_rbsp_trailing_bits(gb);
		h264_print_sps(&sps);
		if (sps.seq_parameter_set_id >= H264_MAX_SPS_COUNT) {
			h264_err("SPS id (%d) out of bounds\n", sps.seq_parameter_set_id);
			goto exit;
		}
		memcpy(&ctx->sub_sps_list[sps.seq_parameter_set_id], &sps, sizeof(sps));
		break;
	default:
		h264_err("Unknown NAL unit type %d\n", nal_unit_type);
		goto exit;
	}

	printf("}\n\n");

exit:
free_rbsp:
	free(rbsp_buf);
	return 0;
}
