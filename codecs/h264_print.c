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

#include "h264.h"
#include <stdio.h>

void h264_print_hrd(struct h264_hrd_parameters *hrd)
{
	printf("\t\t\tcpb_cnt_minus1 = %d\n", hrd->cpb_cnt_minus1);
	printf("\t\t\tbit_rate_scale = %d\n", hrd->bit_rate_scale);
	printf("\t\t\tcpb_size_scale = %d\n", hrd->cpb_size_scale);
	int i;
	for (i = 0; i <= hrd->cpb_cnt_minus1; i++) {
		printf("\t\t\tbit_rate_value_minus1[%d] = %d\n", i,
		       hrd->bit_rate_value_minus1[i]);
		printf("\t\t\tcpb_size_value_minus1[%d] = %d\n", i,
		       hrd->cpb_size_value_minus1[i]);
		printf("\t\t\tcbr_flag[%d] = %d\n", i, hrd->cbr_flag[i]);
	}
	printf("\t\t\tinitial_cpb_removal_delay_length_minus1 = %d\n",
	       hrd->initial_cpb_removal_delay_length_minus1);
	printf("\t\t\tcpb_removal_delay_length_minus1 = %d\n",
	       hrd->cpb_removal_delay_length_minus1);
	printf("\t\t\tdpb_output_delay_length_minus1 = %d\n",
	       hrd->dpb_output_delay_length_minus1);
	printf("\t\t\ttime_offset_length = %d\n", hrd->time_offset_length);
}

void h264_print_sps(struct h264_sps *sps)
{
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
	printf("\tprofile_idc = %d [%s]\n", sps->profile_idc, profile_name);
	printf("\tconstraint_set = %d\n", sps->constraint_set);
	int i, j, k;
	printf("\tlevel_idc = %d\n", sps->level_idc);
	printf("\tseq_parameter_set_id = %d\n", sps->seq_parameter_set_id);
	printf("\tchroma_format_idc = %d\n", sps->chroma_format_idc);
	printf("\tseparate_colour_plane_flag = %d\n", sps->separate_colour_plane_flag);
	printf("\tbit_depth_luma_minus8 = %d\n", sps->bit_depth_luma_minus8);
	printf("\tbit_depth_chroma_minus8 = %d\n", sps->bit_depth_chroma_minus8);
	printf("\tqpprime_y_zero_transform_bypass_flag = %d\n",
	       sps->qpprime_y_zero_transform_bypass_flag);
	printf("\tseq_scaling_matrix_present_flag = %d\n",
	       sps->seq_scaling_matrix_present_flag);
	if (sps->seq_scaling_matrix_present_flag) {
		for (i = 0; i < (sps->chroma_format_idc == 3 ? 12 : 8); i++) {
			printf("\tseq_scaling_list_present_flag[%d] = %d\n", i,
			       sps->seq_scaling_list_present_flag[i]);
			if (sps->seq_scaling_list_present_flag[i]) {
				printf("\tuse_default_scaling_matrix_flag[%d] = %d\n", i,
				       sps->use_default_scaling_matrix_flag[i]);
				if (!sps->use_default_scaling_matrix_flag[i]) {
					for (j = 0; j < (i < 6 ? 16 : 64); j++) {
						if (i < 6)
							printf("\tseq_scaling_list[%d][%d] = %d\n",
							       i, j,
							       sps->seq_scaling_list_4x4
								       [i][j]);
						else
							printf("\tseq_scaling_list[%d][%d] = %d\n",
							       i, j,
							       sps->seq_scaling_list_8x8
								       [i - 6][j]);
					}
				}
			}
		}
	}
	printf("\tlog2_max_frame_num_minus4 = %d\n", sps->log2_max_frame_num_minus4);
	printf("\tpic_order_cnt_type = %d\n", sps->pic_order_cnt_type);
	switch (sps->pic_order_cnt_type) {
	case 0:
		printf("\tlog2_max_pic_order_cnt_lsb_minus4 = %d\n",
		       sps->log2_max_pic_order_cnt_lsb_minus4);
		break;
	case 1:
		printf("\tdelta_pic_order_always_zero_flag = %d\n",
		       sps->delta_pic_order_always_zero_flag);
		printf("\toffset_for_non_ref_pic = %d\n", sps->offset_for_non_ref_pic);
		printf("\toffset_for_top_to_bottom_field = %d\n",
		       sps->offset_for_top_to_bottom_field);
		printf("\tnum_ref_frames_in_pic_order_cnt_cycle = %d\n",
		       sps->num_ref_frames_in_pic_order_cnt_cycle);
		for (i = 0; i < sps->num_ref_frames_in_pic_order_cnt_cycle; i++) {
			printf("\toffset_for_ref_frame[%d] = %d\n", i,
			       sps->offset_for_ref_frame[i]);
		}
		break;
	}
	printf("\tmax_num_ref_frames = %d\n", sps->max_num_ref_frames);
	printf("\tgaps_in_frame_num_value_allowed_flag = %d\n",
	       sps->gaps_in_frame_num_value_allowed_flag);
	printf("\tpic_width_in_mbs_minus1 = %d\n", sps->pic_width_in_mbs_minus1);
	printf("\tpic_height_in_map_units_minus1 = %d\n",
	       sps->pic_height_in_map_units_minus1);
	printf("\tframe_mbs_only_flag = %d\n", sps->frame_mbs_only_flag);
	printf("\tmb_adaptive_frame_field_flag = %d\n",
	       sps->mb_adaptive_frame_field_flag);
	printf("\tdirect_8x8_inference_flag = %d\n", sps->direct_8x8_inference_flag);
	printf("\tframe_cropping_flag = %d\n", sps->frame_cropping_flag);
	printf("\tframe_crop_left_offset = %d\n", sps->frame_crop_left_offset);
	printf("\tframe_crop_right_offset = %d\n", sps->frame_crop_right_offset);
	printf("\tframe_crop_top_offset = %d\n", sps->frame_crop_top_offset);
	printf("\tframe_crop_bottom_offset = %d\n", sps->frame_crop_bottom_offset);
	if (sps->vui_parameters_present_flag) {
		struct h264_vui *vui = &sps->vui;
		printf("\tVUI parameters:\n");
		printf("\t\taspect_ratio_info_present_flag = %d\n",
		       vui->aspect_ratio_info_present_flag);
		printf("\t\taspect_ratio_idc = %d\n", vui->aspect_ratio_idc);
		printf("\t\tsar_width = %d\n", vui->sar_width);
		printf("\t\tsar_height = %d\n", vui->sar_height);
		printf("\t\toverscan_info_present_flag = %d\n",
		       vui->overscan_info_present_flag);
		if (vui->overscan_info_present_flag) {
			printf("\t\toverscan_appropriate_flag = %d\n",
			       vui->overscan_appropriate_flag);
		}
		printf("\t\tvideo_signal_type_present_flag = %d\n",
		       vui->video_signal_type_present_flag);
		printf("\t\tvideo_format = %d\n", vui->video_format);
		printf("\t\tvideo_full_range_flag = %d\n", vui->video_full_range_flag);
		printf("\t\tcolour_description_present_flag = %d\n",
		       vui->colour_description_present_flag);
		printf("\t\tcolour_primaries = %d\n", vui->colour_primaries);
		printf("\t\ttransfer_characteristics = %d\n",
		       vui->transfer_characteristics);
		printf("\t\tmatrix_coefficients = %d\n", vui->matrix_coefficients);
		printf("\t\tchroma_loc_info_present_flag = %d\n",
		       vui->chroma_loc_info_present_flag);
		printf("\t\tchroma_sample_loc_type_top_field = %d\n",
		       vui->chroma_sample_loc_type_top_field);
		printf("\t\tchroma_sample_loc_type_bottom_field = %d\n",
		       vui->chroma_sample_loc_type_bottom_field);
		printf("\t\ttiming_info_present_flag = %d\n",
		       vui->timing_info_present_flag);
		if (vui->timing_info_present_flag) {
			printf("\t\tnum_units_in_tick = %d\n", vui->num_units_in_tick);
			printf("\t\ttime_scale = %d\n", vui->time_scale);
		}
		printf("\t\tfixed_frame_rate_flag = %d\n", vui->fixed_frame_rate_flag);
		if (vui->nal_hrd_parameters_flag) {
			printf("\t\tNAL HRD parameters:\n");
			h264_print_hrd(&vui->nal_hrd_parameters);
		}
		if (vui->vcl_hrd_parameters_flag) {
			printf("\t\tVCL HRD parameters:\n");
			h264_print_hrd(&vui->vcl_hrd_parameters);
		}
		if (vui->nal_hrd_parameters_flag || vui->vcl_hrd_parameters_flag) {
			printf("\t\tlow_delay_hrd_flag = %d\n", vui->low_delay_hrd_flag);
		}
		printf("\t\tpic_struct_present_flag = %d\n",
		       vui->pic_struct_present_flag);
		printf("\t\tbitstream_restriction_present_flag = %d\n",
		       vui->bitstream_restriction_present_flag);
		printf("\t\tmotion_vectors_over_pic_bounduaries_flag = %d\n",
		       vui->motion_vectors_over_pic_bounduaries_flag);
		printf("\t\tmax_bytes_per_pic_denom = %d\n",
		       vui->max_bytes_per_pic_denom);
		printf("\t\tmax_bits_per_mb_denom = %d\n", vui->max_bits_per_mb_denom);
		printf("\t\tlog2_max_mv_length_horizontal = %d\n",
		       vui->log2_max_mv_length_horizontal);
		printf("\t\tlog2_max_mv_length_vertical = %d\n",
		       vui->log2_max_mv_length_vertical);
		printf("\t\tnum_reorder_frames = %d\n", vui->num_reorder_frames);
		printf("\t\tmax_dec_frame_buffering = %d\n",
		       vui->max_dec_frame_buffering);
	}
	if (sps->is_svc) {
		printf("\tinter_layer_deblocking_filter_control_present_flag = %d\n",
		       sps->inter_layer_deblocking_filter_control_present_flag);
		printf("\textended_spatial_scalability_idc = %d\n",
		       sps->extended_spatial_scalability_idc);
		printf("\tchroma_phase_x_plus1_flag = %d\n",
		       sps->chroma_phase_x_plus1_flag);
		printf("\tchroma_phase_y_plus1 = %d\n", sps->chroma_phase_y_plus1);
		printf("\tseq_ref_layer_chroma_phase_x_plus1_flag = %d\n",
		       sps->seq_ref_layer_chroma_phase_x_plus1_flag);
		printf("\tseq_ref_layer_chroma_phase_y_plus1 = %d\n",
		       sps->seq_ref_layer_chroma_phase_y_plus1);
		printf("\tseq_ref_layer_left_offset = %d\n",
		       sps->seq_ref_layer_left_offset);
		printf("\tseq_ref_layer_top_offset = %d\n",
		       sps->seq_ref_layer_top_offset);
		printf("\tseq_ref_layer_right_offset = %d\n",
		       sps->seq_ref_layer_right_offset);
		printf("\tseq_ref_layer_bottom_offset = %d\n",
		       sps->seq_ref_layer_bottom_offset);
		printf("\tseq_tcoeff_level_prediction_flag = %d\n",
		       sps->seq_tcoeff_level_prediction_flag);
		printf("\tadaptive_tcoeff_level_prediction_flag = %d\n",
		       sps->adaptive_tcoeff_level_prediction_flag);
		printf("\tslice_header_restriction_flag = %d\n",
		       sps->slice_header_restriction_flag);
		if (sps->vui_parameters_present_flag) {
			/* XXX */
		}
	}
	if (sps->is_mvc) {
		printf("\tnum_views_minus1 = %d\n", sps->num_views_minus1);
		for (i = 0; i <= sps->num_views_minus1; i++) {
			printf("\tview_id[%d] = %d\n", i, sps->views[i].view_id);
			printf("\tnum_anchor_refs_l0[%d] = %d\n", i,
			       sps->views[i].num_anchor_refs_l0);
			for (j = 1; j < sps->views[i].num_anchor_refs_l0; j++)
				printf("\tanchor_ref_l0[%d][%d] = %d\n", i, j,
				       sps->views[i].anchor_ref_l0[j]);
			printf("\tnum_anchor_refs_l1[%d] = %d\n", i,
			       sps->views[i].num_anchor_refs_l1);
			for (j = 1; j < sps->views[i].num_anchor_refs_l1; j++)
				printf("\tanchor_ref_l1[%d][%d] = %d\n", i, j,
				       sps->views[i].anchor_ref_l1[j]);
			printf("\tnum_non_anchor_refs_l0[%d] = %d\n", i,
			       sps->views[i].num_non_anchor_refs_l0);
			for (j = 1; j < sps->views[i].num_non_anchor_refs_l0; j++)
				printf("\tnon_anchor_ref_l0[%d][%d] = %d\n", i, j,
				       sps->views[i].non_anchor_ref_l0[j]);
			printf("\tnum_non_anchor_refs_l1[%d] = %d\n", i,
			       sps->views[i].num_non_anchor_refs_l1);
			for (j = 1; j < sps->views[i].num_non_anchor_refs_l1; j++)
				printf("\tnon_anchor_ref_l1[%d][%d] = %d\n", i, j,
				       sps->views[i].non_anchor_ref_l1[j]);
		}
		printf("\tnum_level_values_signalled_minus1 = %d\n",
		       sps->num_level_values_signalled_minus1);
		for (i = 0; i <= sps->num_level_values_signalled_minus1; i++) {
			printf("\tlevel_idc[%d] = %d.%d\n", i,
			       sps->levels[i].level_idc / 10,
			       sps->levels[i].level_idc % 10);
			printf("\tnum_applicable_ops_minus1[%d] = %d\n", i,
			       sps->levels[i].num_applicable_ops_minus1);
			for (j = 0; j <= sps->levels[i].num_applicable_ops_minus1; j++) {
				struct h264_sps_mvc_applicable_op *op =
					&sps->levels[i].applicable_ops[j];
				printf("\tapplicable_op_temporal_id[%d][%d] = %d\n", i, j,
				       op->temporal_id);
				printf("\tapplicable_op_num_target_views_minus1[%d][%d] = %d\n",
				       i, j, op->num_target_views_minus1);
				for (k = 0; k <= op->num_target_views_minus1; k++)
					printf("\tapplicable_op_target_view_id[%d][%d][%d] = %d\n",
					       i, j, k, op->target_view_id[k]);
				printf("\tapplicable_op_num_views_minus1[%d][%d] = %d\n",
				       i, j, op->num_views_minus1);
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
	printf("\taux_format_idc = %d\n", sps->aux_format_idc);
	if (sps->aux_format_idc) {
		printf("\tbit_depth_aux_minus8 = %d\n", sps->bit_depth_aux_minus8);
		printf("\talpha_incr_flag = %d\n", sps->alpha_incr_flag);
		printf("\talpha_opaque_value = %d\n", sps->alpha_opaque_value);
		printf("\talpha_transparent_value = %d\n", sps->alpha_transparent_value);
	}
}

void h264_print_pps(struct h264_pps *pps)
{
	printf("\tpic_parameter_set_id = %d\n", pps->pic_parameter_set_id);
	printf("\tseq_parameter_set_id = %d\n", pps->seq_parameter_set_id);
	printf("\tentropy_coding_mode_flag = %d\n", pps->entropy_coding_mode_flag);
	printf("\tbottom_field_pic_order_in_frame_present_flag = %d\n",
	       pps->bottom_field_pic_order_in_frame_present_flag);
	printf("\tnum_slice_groups_minus1 = %d\n", pps->num_slice_groups_minus1);
	if (pps->num_slice_groups_minus1) {
		int i;
		printf("\tslice_group_map_type = %d\n", pps->slice_group_map_type);
		switch (pps->slice_group_map_type) {
		case H264_SLICE_GROUP_MAP_INTERLEAVED:
			for (i = 0; i <= pps->num_slice_groups_minus1; i++) {
				printf("\trun_length_minus1[%d] = %d\n", i,
				       pps->run_length_minus1[i]);
			}
			break;
		case H264_SLICE_GROUP_MAP_DISPERSED:
			break;
		case H264_SLICE_GROUP_MAP_FOREGROUND:
			for (i = 0; i < pps->num_slice_groups_minus1; i++) {
				printf("\ttop_left[%d] = %d\n", i, pps->top_left[i]);
				printf("\tbottom_right[%d] = %d\n", i,
				       pps->bottom_right[i]);
			}
			break;
		case H264_SLICE_GROUP_MAP_CHANGING_BOX:
		case H264_SLICE_GROUP_MAP_CHANGING_VERTICAL:
		case H264_SLICE_GROUP_MAP_CHANGING_HORIZONTAL:
			printf("\tslice_group_change_direction_flag = %d\n",
			       pps->slice_group_change_direction_flag);
			printf("\tslice_group_change_rate_minus1 = %d\n",
			       pps->slice_group_change_rate_minus1);
			break;
		case H264_SLICE_GROUP_MAP_EXPLICIT:
			printf("\tpic_size_in_map_units_minus1 = %d\n",
			       pps->pic_size_in_map_units_minus1);
			for (i = 0; i <= pps->pic_size_in_map_units_minus1; i++)
				printf("\tslice_group_id[%d] = %d\n", i,
				       pps->slice_group_id[i]);
			break;
		}
	}
	printf("\tnum_ref_idx_l0_default_active_minus1 = %d\n",
	       pps->num_ref_idx_l0_default_active_minus1);
	printf("\tnum_ref_idx_l1_default_active_minus1 = %d\n",
	       pps->num_ref_idx_l1_default_active_minus1);
	printf("\tweighted_pred_flag = %d\n", pps->weighted_pred_flag);
	printf("\tweighted_bipred_idc = %d\n", pps->weighted_bipred_idc);
	printf("\tpic_init_qp_minus26 = %d\n", pps->pic_init_qp_minus26);
	printf("\tpic_init_qs_minus26 = %d\n", pps->pic_init_qs_minus26);
	printf("\tchroma_qp_index_offset = %d\n", pps->chroma_qp_index_offset);
	printf("\tdeblocking_filter_control_present_flag = %d\n",
	       pps->deblocking_filter_control_present_flag);
	printf("\tconstrained_intra_pred_flag = %d\n", pps->constrained_intra_pred_flag);
	printf("\tredundant_pic_cnt_present_flag = %d\n",
	       pps->redundant_pic_cnt_present_flag);
	printf("\ttransform_8x8_mode_flag = %d\n", pps->transform_8x8_mode_flag);
	printf("\tpic_scaling_matrix_present_flag = %d\n",
	       pps->pic_scaling_matrix_present_flag);
	if (pps->pic_scaling_matrix_present_flag) {
		int i, j;
		for (i = 0; i < (pps->chroma_format_idc == 3 ? 12 : 8); i++) {
			printf("\tpic_scaling_list_present_flag[%d] = %d\n", i,
			       pps->pic_scaling_list_present_flag[i]);
			if (pps->pic_scaling_list_present_flag[i]) {
				printf("\tuse_default_scaling_matrix_flag[%d] = %d\n", i,
				       pps->use_default_scaling_matrix_flag[i]);
				if (!pps->use_default_scaling_matrix_flag[i]) {
					for (j = 0; j < (i < 6 ? 16 : 64); j++) {
						if (i < 6)
							printf("\tpic_scaling_list[%d][%d] = %d\n",
							       i, j,
							       pps->pic_scaling_list_4x4
								       [i][j]);
						else
							printf("\tpic_scaling_list[%d][%d] = %d\n",
							       i, j,
							       pps->pic_scaling_list_8x8
								       [i - 6][j]);
					}
				}
			}
		}
	}
	printf("\tsecond_chroma_qp_index_offset = %d\n",
	       pps->second_chroma_qp_index_offset);
}

void h264_print_ref_pic_list_modification(struct h264_ref_pic_list_modification *list,
					  char *which)
{
	int i;
	printf("\tref_pic_list_modification_flag_%s = %d\n", which, list->flag);
	for (i = 0; list->list[i].op != 3; i++) {
		int op = list->list[i].op;
		printf("\tmodification_of_pic_nums_idc_%s[%d] = %d\n", which, i, op);
		printf("\tabs_diff_pic_num_minus1_%s[%d] = %d\n", which, i, list->list[i].param);
	}
	printf("\tmodification_of_pic_nums_idc_%s = 3\n", which);
}

void h264_print_pred_weight_table(struct h264_slice *sl)
{
	printf("\tluma_log2_weight_denom = %d\n", sl->luma_log2_weight_denom);
	printf("\tchroma_log2_weight_denom = %d\n", sl->chroma_log2_weight_denom);
	int i;
	for (i = 0; i <= sl->num_ref_idx_l0_active_minus1; i++) {
		printf("\tluma_weight_l0_flag[%d] = %d\n", i, sl->pwt_l0[i].luma_weight_flag);
		printf("\tluma_weight_l0[%d] = %d\n", i, sl->pwt_l0[i].luma_weight);
		printf("\tluma_offset_l0[%d] = %d\n", i, sl->pwt_l0[i].luma_offset);
		printf("\tchroma_weight_l0_flag[%d] = %d\n", i, sl->pwt_l0[i].chroma_weight_flag);
		printf("\tchroma_weight_l0[%d][0] = %d\n", i, sl->pwt_l0[i].chroma_weight[0]);
		printf("\tchroma_weight_l0[%d][1] = %d\n", i, sl->pwt_l0[i].chroma_weight[1]);
		printf("\tchroma_offset_l0[%d][0] = %d\n", i, sl->pwt_l0[i].chroma_offset[0]);
		printf("\tchroma_offset_l0[%d][1] = %d\n", i, sl->pwt_l0[i].chroma_offset[1]);
	}
	if (sl->slice_type_nos == H264_SLICE_TYPE_B) {
		for (i = 0; i <= sl->num_ref_idx_l1_active_minus1; i++) {
			printf("\tluma_weight_l1_flag[%d] = %d\n", i, sl->pwt_l1[i].luma_weight_flag);
			printf("\tluma_weight_l1[%d] = %d\n", i, sl->pwt_l1[i].luma_weight);
			printf("\tluma_offset_l1[%d] = %d\n", i, sl->pwt_l1[i].luma_offset);
			printf("\tchroma_weight_l1_flag[%d] = %d\n", i, sl->pwt_l1[i].chroma_weight_flag);
			printf("\tchroma_weight_l1[%d][0] = %d\n", i, sl->pwt_l1[i].chroma_weight[0]);
			printf("\tchroma_weight_l1[%d][1] = %d\n", i, sl->pwt_l1[i].chroma_weight[1]);
			printf("\tchroma_offset_l1[%d][0] = %d\n", i, sl->pwt_l1[i].chroma_offset[0]);
			printf("\tchroma_offset_l1[%d][1] = %d\n", i, sl->pwt_l1[i].chroma_offset[1]);
		}
	}
}

void h264_print_dec_ref_pic_marking(struct h264_slice *sl)
{
	if (sl->nal_unit_type == H264_NAL_SLICE_IDR) {
		printf("\tno_output_of_prior_pics_flag = %d\n",
		       sl->no_output_of_prior_pics_flag);
		printf("\tlong_term_reference_flag = %d\n", sl->long_term_reference_flag);
	} else {
		printf("\tadaptive_ref_pic_marking_mode_flag = %d\n",
		       sl->adaptive_ref_pic_marking_mode_flag);
		for (int i = 0; i < sl->nb_mmco; i++) {
			int opcode = sl->mmcos[i].opcode;
			if (opcode == H264_MMCO_END)
				break;
			switch (sl->mmcos[i].opcode) {
			case H264_MMCO_END:
				break;
			case H264_MMCO_FORGET_SHORT:
				printf("\tmmco_forget_short = %d\n",
				       sl->mmcos[i].short_pic_num);
				break;
			case H264_MMCO_SHORT_TO_LONG:
				printf("\tmmco_short_to_long = %d %d\n",
				       sl->mmcos[i].short_pic_num, sl->mmcos[i].long_arg);
				break;
			case H264_MMCO_FORGET_LONG:
				printf("\tmmco_forget_long = %d\n",
				       sl->mmcos[i].long_arg);
				break;
			case H264_MMCO_THIS_TO_LONG:
				printf("\tmmco_this_to_long = %d\n",
				       sl->mmcos[i].long_arg);
				break;
			case H264_MMCO_FORGET_LONG_MAX:
				printf("\tmmco_forget_long_max = %d\n",
				       sl->mmcos[i].long_arg);
				break;
			}
		}
	}
}

void h264_print_dec_ref_base_pic_marking(struct h264_nal_svc_header *svc)
{
#if 0
	printf("\tstore_ref_base_pic_flag = %d\n", ref->store_ref_base_pic_flag);
	if ((svc->use_ref_base_pic_flag || ref->store_ref_base_pic_flag) && !svc->idr_flag) {
		printf("\tadaptive_ref_base_pic_marking_mode_flag = %d\n", ref->adaptive_ref_base_pic_marking_mode_flag);
		if (ref->adaptive_ref_base_pic_marking_mode_flag) {
			int i = 0;
			do {
				printf("\tmemory_management_control_operation = %d\n", ref->mmcos[i].memory_management_control_operation);
				switch (ref->mmcos[i].memory_management_control_operation) {
					case H264_MMCO_END:
						break;
					case H264_MMCO_FORGET_SHORT:
						printf("\tdifference_of_pic_nums_minus1 = %d\n", ref->mmcos[i].difference_of_pic_nums_minus1);
						break;
					case H264_MMCO_FORGET_LONG:
						printf("\tlong_term_pic_num = %d\n", ref->mmcos[i].long_term_pic_num);
						break;
				}
			} while (ref->mmcos[i++].memory_management_control_operation != H264_MMCO_END);
		}
	}
#endif
}

void h264_print_slice_header(struct h264_decoder *dec, struct h264_slice *slice)
{
	struct h264_sps *sps = h264_get_sps(dec, slice->pic_parameter_set_id);
	struct h264_pps *pps = h264_get_pps(dec, slice->pic_parameter_set_id);

	//printf("\theader_size = %d\n", slice->header_size);
	printf("\tfirst_mb_in_slice = %d\n", slice->first_mb_in_slice);
	printf("\tslice_type = %d\n", slice->slice_type);
	printf("\tpic_parameter_set_id = %d\n", pps->pic_parameter_set_id);

	if (sps->separate_colour_plane_flag)
		printf("\tcolour_plane_id = %d\n", slice->colour_plane_id);
	printf("\tframe_num = %d\n", slice->frame_num);
	printf("\tfield_pic_flag = %d\n", slice->field_pic_flag);
	printf("\tbottom_field_flag = %d\n", slice->bottom_field_flag);
	if (slice->nal_unit_type == H264_NAL_SLICE_IDR)
		printf("\tidr_pic_id = %d\n", slice->idr_pic_id);
	switch (sps->pic_order_cnt_type) {
	case 0:
		printf("\tpic_order_cnt_lsb = %d\n", slice->pic_order_cnt_lsb);
		printf("\tdelta_pic_order_cnt_bottom = %d\n",
		       slice->delta_pic_order_cnt_bottom);
		break;
	case 1:
		printf("\tdelta_pic_order_cnt[0] = %d\n", slice->delta_pic_order_cnt[0]);
		printf("\tdelta_pic_order_cnt[1] = %d\n", slice->delta_pic_order_cnt[1]);
		break;
	}
	printf("\tredundant_pic_cnt = %d\n", slice->redundant_pic_cnt);
	if (slice->slice_type == H264_SLICE_TYPE_B)
		printf("\tdirect_spatial_mb_pred_flag = %d\n",
		       slice->direct_spatial_mb_pred_flag);
	if (slice->slice_type != H264_SLICE_TYPE_I &&
	    slice->slice_type != H264_SLICE_TYPE_SI) {
		printf("\tnum_ref_idx_active_override_flag = %d\n",
		       slice->num_ref_idx_active_override_flag);
		printf("\tnum_ref_idx_l0_active_minus1 = %d\n",
		       slice->num_ref_idx_l0_active_minus1);
		if (slice->slice_type == H264_SLICE_TYPE_B)
			printf("\tnum_ref_idx_l1_active_minus1 = %d\n",
			       slice->num_ref_idx_l1_active_minus1);
		h264_print_ref_pic_list_modification(&slice->ref_pic_list_modification_l0,
						     "l0");
		if (slice->slice_type == H264_SLICE_TYPE_B)
			h264_print_ref_pic_list_modification(
				&slice->ref_pic_list_modification_l1, "l1");
	}
	if ((pps->weighted_pred_flag && (slice->slice_type == H264_SLICE_TYPE_P ||
					 slice->slice_type == H264_SLICE_TYPE_SP)) ||
	    (pps->weighted_bipred_idc == 1 && slice->slice_type == H264_SLICE_TYPE_B)) {
		printf("\tbase_pred_weight_table_flag = %d\n",
		       slice->base_pred_weight_table_flag);
		if (!slice->base_pred_weight_table_flag) {
			h264_print_pred_weight_table(slice);
		}
	}

	if (slice->nal_ref_idc || (1)) {
		h264_print_dec_ref_pic_marking(slice);
		if (sps->is_svc && !sps->slice_header_restriction_flag)
			h264_print_dec_ref_base_pic_marking(&slice->svc);
	}

	if (slice->slice_type != H264_SLICE_TYPE_I &&
	    slice->slice_type != H264_SLICE_TYPE_SI)
		printf("\tcabac_init_idc = %d\n", slice->cabac_init_idc);
	printf("\tslice_qp_delta = %d\n", slice->slice_qp_delta);
	if (slice->slice_type == H264_SLICE_TYPE_SP)
		printf("\tsp_for_switch_flag = %d\n", slice->sp_for_switch_flag);
	if (slice->slice_type == H264_SLICE_TYPE_SP ||
	    slice->slice_type == H264_SLICE_TYPE_SI)
		printf("\tslice_qs_delta = %d\n", slice->slice_qs_delta);
	printf("\tdisable_deblocking_filter_idc = %d\n",
	       slice->disable_deblocking_filter_idc);
	printf("\tslice_alpha_c0_offset_div2 = %d\n", slice->slice_alpha_c0_offset_div2);
	printf("\tslice_beta_offset_div2 = %d\n", slice->slice_beta_offset_div2);
	if (pps->num_slice_groups_minus1 && pps->slice_group_map_type >= 3 &&
	    pps->slice_group_map_type <= 5) {
		printf("\tslice_group_change_cycle = %d\n",
		       slice->slice_group_change_cycle);
	}

	if (sps->is_svc) {
		/* XXX */
	}
}
