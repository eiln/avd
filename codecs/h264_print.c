/*
 * Copyright 2023 Eileen Yoon <eyn@gmx.com>
 *
 * Based on envytools
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
#include "h264.h"

#define h264_field(a, ...)     printf("\t" a " = %d\n", ##__VA_ARGS__)
#define h264_field2(a, b, ...) printf("\t" a " = %d [%s]\n", b, ##__VA_ARGS__)

static void h264_print_hrd(struct h264_hrd_parameters *hrd)
{
	uint32_t i;

	h264_field("\t\tcpb_cnt_minus1", hrd->cpb_cnt - 1);
	h264_field("\t\tbit_rate_scale", hrd->bit_rate_scale);
	h264_field("\t\tcpb_size_scale", hrd->cpb_size_scale);
	for (i = 0; i < hrd->cpb_cnt; i++) {
		h264_field("\t\tbit_rate_value_minus1[%d]", i,
		       hrd->bit_rate_value[i] - 1);
		h264_field("\t\tcpb_size_value_minus1[%d]", i,
		       hrd->cpb_size_value[i] - 1);
		h264_field("\t\tcbr_flag[%d]", i, hrd->cbr_flag[i]);
	}
	h264_field("\t\tinitial_cpb_removal_delay_length_minus1",
	       hrd->initial_cpb_removal_delay_length - 1);
	h264_field("\t\tcpb_removal_delay_length_minus1",
	       hrd->cpb_removal_delay_length - 1);
	h264_field("\t\tdpb_output_delay_length_minus1",
	       hrd->dpb_output_delay_length - 1);
	h264_field("\t\ttime_offset_length", hrd->time_offset_length);
}

void h264_print_sps(struct h264_sps *sps)
{
	uint32_t i, j, k;
	const char *profile_name = "???";
	switch (sps->profile_idc) {
	case H264_PROFILE_BASELINE:
		profile_name = "Baseline";
		break;
	case H264_PROFILE_MAIN:
		profile_name = "Main";
		break;
	case H264_PROFILE_EXTENDED:
		profile_name = "Extended";
		break;
	case H264_PROFILE_HIGH:
		profile_name = "High";
		break;
	case H264_PROFILE_HIGH_10:
		profile_name = "High 10";
		break;
	case H264_PROFILE_HIGH_422:
		profile_name = "High 4:2:2";
		break;
	case H264_PROFILE_HIGH_444:
		profile_name = "High 4:4:4";
		break;
	case H264_PROFILE_HIGH_444_PRED:
		profile_name = "High 4:4:4 Predictive";
		break;
	case H264_PROFILE_CAVLC_444:
		profile_name = "CAVLC 4:4:4";
		break;
	case H264_PROFILE_SCALABLE_BASELINE:
		profile_name = "Scalable Baseline";
		break;
	case H264_PROFILE_SCALABLE_HIGH:
		profile_name = "Scalable High";
		break;
	case H264_PROFILE_MULTIVIEW_HIGH:
		profile_name = "Multiview High";
		break;
	case H264_PROFILE_STEREO_HIGH:
		profile_name = "Stereo High";
		break;
	}
	h264_field2("profile_idc", sps->profile_idc, profile_name);

	h264_field("constraint_set", sps->constraint_set);
	h264_field("level_idc", sps->level_idc);
	h264_field("seq_parameter_set_id", sps->seq_parameter_set_id);
	h264_field("chroma_format_idc", sps->chroma_format_idc);
	h264_field("separate_colour_plane_flag", sps->separate_colour_plane_flag);
	h264_field("bit_depth_luma_minus8", sps->bit_depth_luma_minus8);
	h264_field("bit_depth_chroma_minus8", sps->bit_depth_chroma_minus8);
	h264_field("qpprime_y_zero_transform_bypass_flag",
	       sps->qpprime_y_zero_transform_bypass_flag);
	h264_field("seq_scaling_matrix_present_flag",
	       sps->seq_scaling_matrix_present_flag);
	if (sps->seq_scaling_matrix_present_flag) {
		for (i = 0; i < (sps->chroma_format_idc == 3 ? 12 : 8); i++) {
			h264_field("seq_scaling_list_present_flag[%d]", i,
			       sps->seq_scaling_list_present_flag[i]);
			if (sps->seq_scaling_list_present_flag[i]) {
				h264_field("use_default_scaling_matrix_flag[%d]", i,
				       sps->use_default_scaling_matrix_flag[i]);
				if (!sps->use_default_scaling_matrix_flag[i]) {
					for (j = 0; j < (i < 6 ? 16 : 64); j++) {
						if (i < 6)
							h264_field("seq_scaling_list[%d][%d]",
							       i, j,
							       sps->seq_scaling_list_4x4[i][j]);
						else
							h264_field("seq_scaling_list[%d][%d]",
							       i, j,
							       sps->seq_scaling_list_8x8[i - 6][j]);
					}
				}
			}
		}
	}
	h264_field("log2_max_frame_num_minus4", sps->log2_max_frame_num - 4);
	h264_field("pic_order_cnt_type", sps->pic_order_cnt_type);
	switch (sps->pic_order_cnt_type) {
	case 0:
		h264_field("log2_max_pic_order_cnt_lsb_minus4",
		       sps->log2_max_pic_order_cnt_lsb - 4);
		break;
	case 1:
		h264_field("delta_pic_order_always_zero_flag",
		       sps->delta_pic_order_always_zero_flag);
		h264_field("offset_for_non_ref_pic", sps->offset_for_non_ref_pic);
		h264_field("offset_for_top_to_bottom_field",
		       sps->offset_for_top_to_bottom_field);
		h264_field("num_ref_frames_in_pic_order_cnt_cycle",
		       sps->num_ref_frames_in_pic_order_cnt_cycle);
		for (i = 0; i < sps->num_ref_frames_in_pic_order_cnt_cycle; i++) {
			h264_field("offset_for_ref_frame[%d]", i,
			       sps->offset_for_ref_frame[i]);
		}
		break;
	}
	h264_field("max_num_ref_frames", sps->max_num_ref_frames);
	h264_field("gaps_in_frame_num_value_allowed_flag",
	       sps->gaps_in_frame_num_value_allowed_flag);

	h264_field("pic_width_in_mbs_minus1", sps->pic_width_in_mbs - 1);
	h264_field("pic_height_in_map_units_minus1",
	       sps->pic_height_in_map_units - 1);
	h264_field("frame_mbs_only_flag", sps->frame_mbs_only_flag);
	h264_field("mb_adaptive_frame_field_flag",
	       sps->mb_adaptive_frame_field_flag);
	h264_field("direct_8x8_inference_flag", sps->direct_8x8_inference_flag);
	h264_field("frame_cropping_flag", sps->frame_cropping_flag);
	h264_field("frame_crop_left_offset", sps->frame_crop_left_offset);
	h264_field("frame_crop_right_offset", sps->frame_crop_right_offset);
	h264_field("frame_crop_top_offset", sps->frame_crop_top_offset);
	h264_field("frame_crop_bottom_offset", sps->frame_crop_bottom_offset);

	if (sps->vui_parameters_present_flag) {
		struct h264_vui *vui = &sps->vui;
		printf("\tVUI parameters:\n");
		h264_field("\taspect_ratio_info_present_flag",
		       vui->aspect_ratio_info_present_flag);
		h264_field("\taspect_ratio_idc", vui->aspect_ratio_idc);
		h264_field("\tsar_width", vui->sar_width);
		h264_field("\tsar_height", vui->sar_height);
		h264_field("\toverscan_info_present_flag",
		       vui->overscan_info_present_flag);
		if (vui->overscan_info_present_flag) {
			h264_field("\toverscan_appropriate_flag",
			       vui->overscan_appropriate_flag);
		}
		h264_field("\tvideo_signal_type_present_flag",
		       vui->video_signal_type_present_flag);
		h264_field("\tvideo_format", vui->video_format);
		h264_field("\tvideo_full_range_flag", vui->video_full_range_flag);
		h264_field("\tcolour_description_present_flag",
		       vui->colour_description_present_flag);
		h264_field("\tcolour_primaries", vui->colour_primaries);
		h264_field("\ttransfer_characteristics",
		       vui->transfer_characteristics);
		h264_field("\tmatrix_coefficients", vui->matrix_coefficients);
		h264_field("\tchroma_loc_info_present_flag",
		       vui->chroma_loc_info_present_flag);
		h264_field("\tchroma_sample_loc_type_top_field",
		       vui->chroma_sample_loc_type_top_field);
		h264_field("\tchroma_sample_loc_type_bottom_field",
		       vui->chroma_sample_loc_type_bottom_field);
		h264_field("\ttiming_info_present_flag",
		       vui->timing_info_present_flag);
		if (vui->timing_info_present_flag) {
			h264_field("\tnum_units_in_tick", vui->num_units_in_tick);
			h264_field("\ttime_scale", vui->time_scale);
		}
		h264_field("\tfixed_frame_rate_flag", vui->fixed_frame_rate_flag);
		if (vui->nal_hrd_parameters_flag) {
			printf("\tNAL HRD parameters:\n");
			h264_print_hrd(&vui->nal_hrd_parameters);
		}
		if (vui->vcl_hrd_parameters_flag) {
			printf("\tVCL HRD parameters:\n");
			h264_print_hrd(&vui->vcl_hrd_parameters);
		}
		if (vui->nal_hrd_parameters_flag || vui->vcl_hrd_parameters_flag) {
			h264_field("\tlow_delay_hrd_flag", vui->low_delay_hrd_flag);
		}
		h264_field("\tpic_struct_present_flag",
		       vui->pic_struct_present_flag);
		h264_field("\tbitstream_restriction_present_flag",
		       vui->bitstream_restriction_present_flag);
		h264_field("\tmotion_vectors_over_pic_bounduaries_flag",
		       vui->motion_vectors_over_pic_bounduaries_flag);
		h264_field("\tmax_bytes_per_pic_denom",
		       vui->max_bytes_per_pic_denom);
		h264_field("\tmax_bits_per_mb_denom", vui->max_bits_per_mb_denom);
		h264_field("\tlog2_max_mv_length_horizontal",
		       vui->log2_max_mv_length_horizontal);
		h264_field("\tlog2_max_mv_length_vertical",
		       vui->log2_max_mv_length_vertical);
		h264_field("\tnum_reorder_frames", vui->num_reorder_frames);
		h264_field("\tmax_dec_frame_buffering",
		       vui->max_dec_frame_buffering);
	}

	if (sps->is_svc) {
		h264_field("inter_layer_deblocking_filter_control_present_flag",
		       sps->inter_layer_deblocking_filter_control_present_flag);
		h264_field("extended_spatial_scalability_idc",
		       sps->extended_spatial_scalability_idc);
		h264_field("chroma_phase_x_plus1_flag",
		       sps->chroma_phase_x_plus1_flag);
		h264_field("chroma_phase_y_plus1", sps->chroma_phase_y_plus1);
		h264_field("seq_ref_layer_chroma_phase_x_plus1_flag",
		       sps->seq_ref_layer_chroma_phase_x_plus1_flag);
		h264_field("seq_ref_layer_chroma_phase_y_plus1",
		       sps->seq_ref_layer_chroma_phase_y_plus1);
		h264_field("seq_ref_layer_left_offset",
		       sps->seq_ref_layer_left_offset);
		h264_field("seq_ref_layer_top_offset",
		       sps->seq_ref_layer_top_offset);
		h264_field("seq_ref_layer_right_offset",
		       sps->seq_ref_layer_right_offset);
		h264_field("seq_ref_layer_bottom_offset",
		       sps->seq_ref_layer_bottom_offset);
		h264_field("seq_tcoeff_level_prediction_flag",
		       sps->seq_tcoeff_level_prediction_flag);
		h264_field("adaptive_tcoeff_level_prediction_flag",
		       sps->adaptive_tcoeff_level_prediction_flag);
		h264_field("slice_header_restriction_flag",
		       sps->slice_header_restriction_flag);
		if (sps->vui_parameters_present_flag) {
			/* XXX */
		}
	}

	if (sps->is_mvc) {
		h264_field("num_views_minus1", sps->num_views - 1);
		for (i = 0; i < sps->num_views; i++) {
			h264_field("view_id[%d]", i, sps->views[i].view_id);
			h264_field("num_anchor_refs_l0[%d]", i,
			       sps->views[i].num_anchor_refs_l0);
			for (j = 1; j < sps->views[i].num_anchor_refs_l0; j++)
				h264_field("anchor_ref_l0[%d][%d]", i, j,
				       sps->views[i].anchor_ref_l0[j]);
			h264_field("num_anchor_refs_l1[%d]", i,
			       sps->views[i].num_anchor_refs_l1);
			for (j = 1; j < sps->views[i].num_anchor_refs_l1; j++)
				h264_field("anchor_ref_l1[%d][%d]", i, j,
				       sps->views[i].anchor_ref_l1[j]);
			h264_field("num_non_anchor_refs_l0[%d]", i,
			       sps->views[i].num_non_anchor_refs_l0);
			for (j = 1; j < sps->views[i].num_non_anchor_refs_l0; j++)
				h264_field("non_anchor_ref_l0[%d][%d]", i, j,
				       sps->views[i].non_anchor_ref_l0[j]);
			h264_field("num_non_anchor_refs_l1[%d]", i,
			       sps->views[i].num_non_anchor_refs_l1);
			for (j = 1; j < sps->views[i].num_non_anchor_refs_l1; j++)
				h264_field("non_anchor_ref_l1[%d][%d]", i, j,
				       sps->views[i].non_anchor_ref_l1[j]);
		}
		h264_field("num_level_values_signalled_minus1",
		       sps->num_level_values_signalled - 1);
		for (i = 0; i < sps->num_level_values_signalled; i++) {
			h264_field("level_idc[%d]", i, sps->levels[i].level_idc);
			h264_field("num_applicable_ops_minus1[%d]", i,
			       sps->levels[i].num_applicable_ops - 1);
			for (j = 0; j < sps->levels[i].num_applicable_ops; j++) {
				struct h264_sps_mvc_applicable_op *op =
					&sps->levels[i].applicable_ops[j];
				h264_field("applicable_op_temporal_id[%d][%d]", i, j,
				       op->temporal_id);
				h264_field("applicable_op_num_target_views_minus1[%d][%d]",
				       i, j, op->num_target_views - 1);
				for (k = 0; k < op->num_target_views; k++)
					h264_field("applicable_op_target_view_id[%d][%d][%d]",
					       i, j, k, op->target_view_id[k]);
				h264_field("applicable_op_num_views_minus1[%d][%d]",
				       i, j, op->num_views - 1);
			}
		}
		if (sps->mvc_vui_parameters_present_flag) {
			/* XXX */
		}
	}
}

void h264_print_sps_ext(struct h264_sps *sps)
{
	printf("Sequence parameter set extension:\n");
	h264_field("aux_format_idc", sps->aux_format_idc);
	if (sps->aux_format_idc) {
		h264_field("bit_depth_aux_minus8", sps->bit_depth_aux_minus8);
		h264_field("alpha_incr_flag", sps->alpha_incr_flag);
		h264_field("alpha_opaque_value", sps->alpha_opaque_value);
		h264_field("alpha_transparent_value", sps->alpha_transparent_value);
	}
}

void h264_print_pps(struct h264_pps *pps)
{
	uint32_t i;

	h264_field("pic_parameter_set_id", pps->pic_parameter_set_id);
	h264_field("seq_parameter_set_id", pps->seq_parameter_set_id);
	h264_field("entropy_coding_mode_flag", pps->entropy_coding_mode_flag);
	h264_field("bottom_field_pic_order_in_frame_present_flag",
	       pps->bottom_field_pic_order_in_frame_present_flag);

	h264_field("num_slice_groups_minus1", pps->num_slice_groups - 1);
	if (pps->num_slice_groups) {
		h264_field("slice_group_map_type", pps->slice_group_map_type);
		switch (pps->slice_group_map_type) {
		case H264_SLICE_GROUP_MAP_INTERLEAVED:
			for (i = 0; i < pps->num_slice_groups; i++) {
				h264_field("run_length[%d]", i,
				       pps->run_length[i]);
			}
			break;
		case H264_SLICE_GROUP_MAP_DISPERSED:
			break;
		case H264_SLICE_GROUP_MAP_FOREGROUND:
			for (i = 0; i < pps->num_slice_groups; i++) {
				h264_field("top_left[%d]", i, pps->top_left[i]);
				h264_field("bottom_right[%d]", i, pps->bottom_right[i]);
			}
			break;
		case H264_SLICE_GROUP_MAP_CHANGING_BOX:
		case H264_SLICE_GROUP_MAP_CHANGING_VERTICAL:
		case H264_SLICE_GROUP_MAP_CHANGING_HORIZONTAL:
			h264_field("slice_group_change_direction_flag",
			       pps->slice_group_change_direction_flag);
			h264_field("slice_group_change_rate_minus1",
			       pps->slice_group_change_rate - 1);
			break;
		case H264_SLICE_GROUP_MAP_EXPLICIT:
			h264_field("pic_size_in_map_units_minus1",
			       pps->pic_size_in_map_units - 1);
			for (i = 0; i < pps->pic_size_in_map_units; i++)
				h264_field("slice_group_id[%d]", i,
				       pps->slice_group_id[i]);
			break;
		}
	}

	h264_field("num_ref_idx_l0_default_active_minus1",
	       pps->num_ref_idx_l0_default_active - 1);
	h264_field("num_ref_idx_l1_default_active_minus1",
	       pps->num_ref_idx_l1_default_active - 1);

	h264_field("weighted_pred_flag", pps->weighted_pred_flag);
	h264_field("weighted_bipred_idc", pps->weighted_bipred_idc);
	h264_field("pic_init_qp_minus26", pps->pic_init_qp_minus26);
	h264_field("pic_init_qs_minus26", pps->pic_init_qs_minus26);
	h264_field("chroma_qp_index_offset", pps->chroma_qp_index_offset);

	h264_field("deblocking_filter_control_present_flag",
	       pps->deblocking_filter_control_present_flag);
	h264_field("constrained_intra_pred_flag", pps->constrained_intra_pred_flag);
	h264_field("redundant_pic_cnt_present_flag",
	       pps->redundant_pic_cnt_present_flag);

	h264_field("transform_8x8_mode_flag", pps->transform_8x8_mode_flag);
	h264_field("pic_scaling_matrix_present_flag",
	       pps->pic_scaling_matrix_present_flag);
	if (pps->pic_scaling_matrix_present_flag) {
		int i, j;
		for (i = 0; i < (pps->chroma_format_idc == 3 ? 12 : 8); i++) {
			h264_field("pic_scaling_list_present_flag[%d]", i,
			       pps->pic_scaling_list_present_flag[i]);
			if (pps->pic_scaling_list_present_flag[i]) {
				h264_field("use_default_scaling_matrix_flag[%d]", i,
				       pps->use_default_scaling_matrix_flag[i]);
				if (!pps->use_default_scaling_matrix_flag[i]) {
					for (j = 0; j < (i < 6 ? 16 : 64); j++) {
						if (i < 6)
							h264_field("pic_scaling_list[%d][%d]",
							       i, j,
							       pps->pic_scaling_list_4x4[i][j]);
						else
							h264_field("pic_scaling_list[%d][%d]",
							       i, j,
							       pps->pic_scaling_list_8x8[i - 6][j]);
					}
				}
			}
		}
	}
	h264_field("second_chroma_qp_index_offset",
	       pps->second_chroma_qp_index_offset);
}

static void h264_print_ref_pic_list_modification(struct h264_ref_pic_list_modification *list,
					  char *which)
{
	uint32_t i = 0;
	h264_field("ref_pic_list_modification_flag_%s", which, list->flag);
	for (i = 0; list->list[i].op != 3; i++) {
		h264_field("modification_of_pic_nums_idc_%s[%d]", which, i, list->list[i].op);
		h264_field("abs_diff_pic_num_minus1_%s[%d]", which, i, list->list[i].param);
	}
	h264_field("modification_of_pic_nums_idc_%s[%d]", which, i, 3);
}

static void h264_print_pred_weight_table(struct h264_slice *sl)
{
	uint32_t i;
	h264_field("luma_log2_weight_denom", sl->luma_log2_weight_denom);
	h264_field("chroma_log2_weight_denom", sl->chroma_log2_weight_denom);
	for (i = 0; i < sl->num_ref_idx_l0_active; i++) {
		h264_field("luma_weight_l0_flag[%d]", i, sl->pwt_l0[i].luma_weight_flag);
		h264_field("luma_weight_l0[%d]", i, sl->pwt_l0[i].luma_weight);
		h264_field("luma_offset_l0[%d]", i, sl->pwt_l0[i].luma_offset);
		h264_field("chroma_weight_l0_flag[%d]", i, sl->pwt_l0[i].chroma_weight_flag);
		h264_field("chroma_weight_l0[%d][0]", i, sl->pwt_l0[i].chroma_weight[0]);
		h264_field("chroma_weight_l0[%d][1]", i, sl->pwt_l0[i].chroma_weight[1]);
		h264_field("chroma_offset_l0[%d][0]", i, sl->pwt_l0[i].chroma_offset[0]);
		h264_field("chroma_offset_l0[%d][1]", i, sl->pwt_l0[i].chroma_offset[1]);
	}
	if (sl->slice_type_nos == H264_SLICE_TYPE_B) {
		for (i = 0; i < sl->num_ref_idx_l1_active; i++) {
			h264_field("luma_weight_l1_flag[%d]", i, sl->pwt_l1[i].luma_weight_flag);
			h264_field("luma_weight_l1[%d]", i, sl->pwt_l1[i].luma_weight);
			h264_field("luma_offset_l1[%d]", i, sl->pwt_l1[i].luma_offset);
			h264_field("chroma_weight_l1_flag[%d]", i, sl->pwt_l1[i].chroma_weight_flag);
			h264_field("chroma_weight_l1[%d][0]", i, sl->pwt_l1[i].chroma_weight[0]);
			h264_field("chroma_weight_l1[%d][1]", i, sl->pwt_l1[i].chroma_weight[1]);
			h264_field("chroma_offset_l1[%d][0]", i, sl->pwt_l1[i].chroma_offset[0]);
			h264_field("chroma_offset_l1[%d][1]", i, sl->pwt_l1[i].chroma_offset[1]);
		}
	}
}

static void h264_print_dec_ref_pic_marking(struct h264_slice *sl)
{
	int i;

	if (sl->nal_unit_type == H264_NAL_SLICE_IDR) {
		h264_field("no_output_of_prior_pics_flag",
		       sl->no_output_of_prior_pics_flag);
		h264_field("long_term_reference_flag", sl->long_term_reference_flag);
	} else {
		h264_field("adaptive_ref_pic_marking_mode_flag",
		       sl->adaptive_ref_pic_marking_mode_flag);
		for (i = 0; i < sl->num_mmcos; i++) {
			switch (sl->mmcos[i].opcode) {
			case H264_MMCO_END:
				break;
			case H264_MMCO_FORGET_SHORT:
				h264_field("mmco_forget_short[%d]", i,
					sl->mmcos[i].short_pic_num);
				break;
			case H264_MMCO_SHORT_TO_LONG: // TODO long args
				h264_field("mmco_short_to_long[%d]", i,
				       sl->mmcos[i].short_pic_num);
				break;
			case H264_MMCO_FORGET_LONG:
				h264_field("mmco_forget_long[%d]", i,
				       sl->mmcos[i].long_arg);
				break;
			case H264_MMCO_THIS_TO_LONG:
				h264_field("mmco_this_to_long[%d]", i,
				       sl->mmcos[i].long_arg);
				break;
			case H264_MMCO_FORGET_LONG_MAX:
				h264_field("mmco_forget_long_max[%d]", i,
				       sl->mmcos[i].long_arg);
				break;
			case H264_MMCO_FORGET_ALL:
				break; /* XXX */
			}
		}
	}
}

static void h264_print_dec_ref_base_pic_marking(struct h264_slice *sl,
					        struct h264_nal_svc_header *svc)
{
	int i;

	h264_field("store_ref_base_pic_flag", sl->store_ref_base_pic_flag);
	if ((svc->use_ref_base_pic_flag || sl->store_ref_base_pic_flag) && !svc->idr_flag) {
		h264_field("adaptive_ref_base_pic_marking_mode_flag", sl->adaptive_ref_base_pic_marking_mode_flag);
		for (i = 0; i < sl->num_base_mmcos; i++) {
			switch (sl->base_mmcos[i].opcode) {
				case H264_MMCO_END:
					break;
				case H264_MMCO_FORGET_SHORT:
					h264_field("base_mmco_forget_short[%d]", i,
						sl->base_mmcos[i].short_pic_num);
					break;
				case H264_MMCO_FORGET_LONG:
					h264_field("base_mmco_forget_long[%d]", i,
						sl->base_mmcos[i].long_arg);
					break;
				default:
					break;
			}
		}
	}
}

void h264_print_slice_header(struct h264_context *ctx, struct h264_slice *sl)
{
	struct h264_sps *sps = h264_get_sps(ctx, sl->pic_parameter_set_id);
	struct h264_pps *pps = h264_get_pps(ctx, sl->pic_parameter_set_id);

	h264_field("first_mb_in_slice", sl->first_mb_in_slice);
	h264_field("slice_type", sl->slice_type);
	h264_field("pic_parameter_set_id", pps->pic_parameter_set_id);
	if (sps->separate_colour_plane_flag)
		h264_field("colour_plane_id", sl->colour_plane_id);

	h264_field("frame_num", sl->frame_num);
	h264_field("field_pic_flag", sl->field_pic_flag);
	h264_field("bottom_field_flag", sl->bottom_field_flag);
	if (sl->nal_unit_type == H264_NAL_SLICE_IDR)
		h264_field("idr_pic_id", sl->idr_pic_id);
	switch (sps->pic_order_cnt_type) {
	case 0:
		h264_field("pic_order_cnt_lsb", sl->pic_order_cnt_lsb);
		h264_field("delta_pic_order_cnt_bottom",
		       sl->delta_pic_order_cnt_bottom);
		break;
	case 1:
		h264_field("delta_pic_order_cnt[0]", sl->delta_pic_order_cnt[0]);
		h264_field("delta_pic_order_cnt[1]", sl->delta_pic_order_cnt[1]);
		break;
	}
	h264_field("redundant_pic_cnt", sl->redundant_pic_cnt);
	if (sl->slice_type == H264_SLICE_TYPE_B)
		h264_field("direct_spatial_mb_pred_flag",
		       sl->direct_spatial_mb_pred_flag);

	if (sl->slice_type != H264_SLICE_TYPE_I &&
	    sl->slice_type != H264_SLICE_TYPE_SI) {
		h264_field("num_ref_idx_active_override_flag",
		       sl->num_ref_idx_active_override_flag);
		h264_field("num_ref_idx_l0_active_minus1",
		       sl->num_ref_idx_l0_active - 1);
		if (sl->slice_type == H264_SLICE_TYPE_B)
			h264_field("num_ref_idx_l1_active_minus1",
			       sl->num_ref_idx_l1_active - 1);
		h264_print_ref_pic_list_modification(&sl->ref_pic_list_modification_l0,
						     "l0");
		if (sl->slice_type == H264_SLICE_TYPE_B)
			h264_print_ref_pic_list_modification(
				&sl->ref_pic_list_modification_l1, "l1");
	}
	if ((pps->weighted_pred_flag && (sl->slice_type == H264_SLICE_TYPE_P ||
					 sl->slice_type == H264_SLICE_TYPE_SP)) ||
	    (pps->weighted_bipred_idc == 1 && sl->slice_type == H264_SLICE_TYPE_B)) {
		h264_field("base_pred_weight_table_flag",
		       sl->base_pred_weight_table_flag);
		if (!sl->base_pred_weight_table_flag) {
			h264_print_pred_weight_table(sl);
		}
	}

	h264_print_dec_ref_pic_marking(sl);
	if (sps->is_svc && !sps->slice_header_restriction_flag)
		h264_print_dec_ref_base_pic_marking(sl, &sl->svc);

	if (sl->slice_type != H264_SLICE_TYPE_I &&
	    sl->slice_type != H264_SLICE_TYPE_SI)
		h264_field("cabac_init_idc", sl->cabac_init_idc);

	h264_field("slice_qp_delta", sl->slice_qp_delta);
	if (sl->slice_type == H264_SLICE_TYPE_SP)
		h264_field("sp_for_switch_flag", sl->sp_for_switch_flag);
	if (sl->slice_type == H264_SLICE_TYPE_SP ||
	    sl->slice_type == H264_SLICE_TYPE_SI)
		h264_field("slice_qs_delta", sl->slice_qs_delta);

	h264_field("disable_deblocking_filter_idc",
	       sl->disable_deblocking_filter_idc);
	h264_field("slice_alpha_c0_offset_div2", sl->slice_alpha_c0_offset_div2);
	h264_field("slice_beta_offset_div2", sl->slice_beta_offset_div2);
	if (pps->num_slice_groups && pps->slice_group_map_type >= 3 &&
		pps->slice_group_map_type <= 5) {
		h264_field("slice_group_change_cycle", sl->slice_group_change_cycle);
	}

	if (sps->is_svc) {
		/* XXX */
	}
}
