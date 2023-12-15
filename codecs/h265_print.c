
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

#include "h265.h"
#include "h265_print.h"

static void h265_print_sublayer_hdr(struct hevc_sublayer_hdr_params *par,
                        unsigned int nb_cpb, int subpic_params_present)
{
    int i;

    for (i = 0; i < nb_cpb; i++) {
        h265_fieldt("bit_rate_value_minus1[%d]", i, par->bit_rate_value_minus1[i]);
        h265_fieldt("cpb_size_value_minus1[%d]", i, par->cpb_size_value_minus1[i]);
        if (subpic_params_present) {
            h265_fieldt("cpb_size_du_value_minus1[%d]", i, par->cpb_size_du_value_minus1[i]);
            h265_fieldt("bit_rate_du_value_minus1[%d]", i, par->bit_rate_du_value_minus1[i]);
        }
        h265_fieldt("cbr_flag[%d]", i, par->cbr_flag[i]);
    }
}

static void h265_print_hdr(struct hevc_hdr_params *hdr, int common_inf_present, int max_sublayers)
{
    int i;

    if (common_inf_present) {
        h265_field("nal_hrd_parameters_present_flag", hdr->nal_hrd_parameters_present_flag);
        h265_field("vcl_hrd_parameters_present_flag", hdr->vcl_hrd_parameters_present_flag);
        if (hdr->nal_hrd_parameters_present_flag || hdr->vcl_hrd_parameters_present_flag) {
            h265_field("sub_pic_hrd_params_present_flag", hdr->sub_pic_hrd_params_present_flag);
            if (hdr->sub_pic_hrd_params_present_flag) {
                h265_field("tick_divisor_minus2", hdr->tick_divisor_minus2);
                h265_field("du_cpb_removal_delay_increment_length_minus1", hdr->du_cpb_removal_delay_increment_length_minus1);
                h265_field("sub_pic_cpb_params_in_pic_timing_sei_flag", hdr->sub_pic_cpb_params_in_pic_timing_sei_flag);
                h265_field("dpb_output_delay_du_length_minus1", hdr->dpb_output_delay_du_length_minus1);
            }
            h265_field("bit_rate_scale", hdr->nal_hrd_parameters_present_flag);
            h265_field("cpb_size_scale", hdr->vcl_hrd_parameters_present_flag);
            if (hdr->sub_pic_hrd_params_present_flag)
                h265_field("cpb_size_du_scale", hdr->cpb_size_du_scale);

            h265_field("initial_cpb_removal_delay_length_minus1", hdr->initial_cpb_removal_delay_length_minus1);
            h265_field("au_cpb_removal_delay_length_minus1", hdr->au_cpb_removal_delay_length_minus1);
            h265_field("dpb_output_delay_length_minus1", hdr->dpb_output_delay_length_minus1);
        }
    }

    for (i = 0; i < max_sublayers; i++) {
        h265_field("fixed_pic_rate_general_flag[%d]", i, hdr->fixed_pic_rate_general_flag[i]);
        if (!hdr->fixed_pic_rate_general_flag[i])
            h265_field("fixed_pic_rate_within_cvs_flag[%d]", i, hdr->fixed_pic_rate_within_cvs_flag[i]);
        if (hdr->fixed_pic_rate_within_cvs_flag[i] || hdr->fixed_pic_rate_general_flag[i])
            h265_field("elemental_duration_in_tc_minus1[%d]", i, hdr->elemental_duration_in_tc_minus1[i]);
        else
            h265_field("low_delay_hrd_flag[%d]", i, hdr->low_delay_hrd_flag[i]);
        if (!hdr->low_delay_hrd_flag[i])
            h265_field("hdr->cpb_cnt_minus1[%d]", i, hdr->cpb_cnt_minus1[i]);

        if (hdr->nal_hrd_parameters_present_flag)
            h265_print_sublayer_hdr(&hdr->nal_params[i], hdr->cpb_cnt_minus1[i]+1,
                                    hdr->sub_pic_hrd_params_present_flag);

        if (hdr->vcl_hrd_parameters_present_flag)
            h265_print_sublayer_hdr(&hdr->vcl_params[i], hdr->cpb_cnt_minus1[i]+1,
                                    hdr->sub_pic_hrd_params_present_flag);
    }
}

static void h265_print_ptl_common(struct hevc_ptl_common *ptl, const char *name)
{
    #define h265_ptl_field(a) (h265_fieldt("%s_" #a, name, ptl->a))
    h265_ptl_field(profile_space);
    h265_ptl_field(tier_flag);
    h265_ptl_field(profile_idc);
    h265_ptl_field(progressive_source_flag);
    h265_ptl_field(interlaced_source_flag);
    h265_ptl_field(non_packed_constraint_flag);
    h265_ptl_field(frame_only_constraint_flag);

    h265_ptl_field(max_12bit_constraint_flag);
    h265_ptl_field(max_10bit_constraint_flag);
    h265_ptl_field(max_8bit_constraint_flag);
    h265_ptl_field(max_422chroma_constraint_flag);
    h265_ptl_field(max_420chroma_constraint_flag);
    h265_ptl_field(max_monochrome_constraint_flag);

    h265_ptl_field(intra_constraint_flag);
    h265_ptl_field(one_picture_only_constraint_flag);
    h265_ptl_field(lower_bit_rate_constraint_flag);
    h265_ptl_field(max_14bit_constraint_flag);

    h265_ptl_field(inbld_flag);
    h265_ptl_field(level_idc);
    #undef h265_ptl_field
}

static void h265_print_ptl(struct hevc_ptl *ptl, int max_num_sub_layers)
{
    int i;

    h265_header("Profile tier level:");
    h265_print_ptl_common(&ptl->general_ptl, "general");
    for (i = 0; i < max_num_sub_layers - 1; i++) {
        if (ptl->sub_layer_level_present_flag[i])
            h265_print_ptl_common(&ptl->sub_layer_ptl[i], "sub_layer");
    }
}

void h265_print_nal_vps(struct hevc_vps *vps)
{
    int i;

    h265_field("vps_video_parameter_set_id", vps->vps_id);
    h265_field("vps_base_layer_internal_flag", vps->vps_base_layer_internal_flag);
    h265_field("vps_base_layer_available_flag", vps->vps_base_layer_available_flag);
    h265_field("vps_max_layers", vps->vps_max_layers);
    h265_field("vps_max_sub_layers", vps->vps_max_sub_layers);
    h265_field("vps_temporal_id_nesting_flag", vps->vps_temporal_id_nesting_flag);
    h265_print_ptl(&vps->ptl, vps->vps_max_sub_layers);

    h265_field("vps_sub_layer_ordering_info_present_flag", vps->vps_sub_layer_ordering_info_present_flag);
    for (i = 0; i < vps->vps_max_sub_layers; i++) {
        h265_field("vps_max_dec_pic_buffering_minus1[%d]", i, vps->vps_max_dec_pic_buffering[i]-1);
        h265_field("vps_max_num_reorder_pics[%d]", i, vps->vps_max_num_reorder_pics[i]);
        h265_field("vps_max_latency_increase_plus1[%d]", i, vps->vps_max_latency_increase[i]+1);
    }

    h265_field("vps_max_layer_id", vps->vps_max_layer_id);
    h265_field("vps_num_layer_sets", vps->vps_num_layer_sets);
    h265_field("vps_timing_info_present_flag", vps->vps_timing_info_present_flag);
    if (vps->vps_timing_info_present_flag) {
        h265_field("vps_num_units_in_tick", vps->vps_num_units_in_tick);
        h265_field("vps_time_scale", vps->vps_time_scale);
        h265_field("vps_poc_proportional_to_timing_flag", vps->vps_poc_proportional_to_timing_flag);
        if (vps->vps_poc_proportional_to_timing_flag)
            h265_field("vps_num_ticks_poc_diff_one", vps->vps_num_ticks_poc_diff_one);
        h265_field("vps_num_hrd_parameters", vps->vps_num_hrd_parameters);
        for (i = 0; i < vps->vps_num_hrd_parameters; i++) {
            h265_field("hrd_layer_set_idx[%d]", i, vps->hrd_layer_set_idx[i]);
            h265_field("vps->cprms_present_flag[%d]", i, vps->cprms_present_flag[i]);
            h265_print_hdr(&vps->hdr[i], vps->cprms_present_flag[i], vps->vps_max_sub_layers);
        }
    }
}

static void h265_print_scaling_list(ScalingList *sl, const char *which)
{
    int size_id, matrix_id;
    int i;

    for (size_id = 0; size_id < 4; size_id++) {
        for (matrix_id = 0; matrix_id < 6; matrix_id += ((size_id == 3) ? 3 : 1)) {
            h265_fieldt("%s_scaling_list_pred_mode_flag[%d][%d]",
                which, size_id, matrix_id,
                sl->scaling_list_pred_mode_flag[size_id][matrix_id]);
            if (!sl->scaling_list_pred_mode_flag[size_id][matrix_id])
                h265_fieldt("%s_scaling_list_pred_matrix_id_delta[%d][%d]",
                    which, size_id, matrix_id,
                    sl->scaling_list_pred_matrix_id_delta[size_id][matrix_id]);
            for (i = 0; i < ((size_id == 0) ? 16 : 64); i++) {
                int size = 1 << (size_id + 2);
                h265_fieldt("%s_scaling_list_%dx%d[%d][%d]",
                    which, size, size, matrix_id, i, sl->sl[size_id][matrix_id][i]);
            }
        }
    }

    for (size_id = 0; size_id < 2; size_id++) {
        for (matrix_id = 0; matrix_id < 6; matrix_id++) {
            h265_fieldt("%s_scaling_list_delta_coeff[%d][%d]",
                    which, size_id, matrix_id, sl->sl_dc[size_id][matrix_id]);
        }
    }
}

static void h265_print_st_rps(struct h265_context *s, struct hevc_short_term_rps *rps)
{
    int i;
    h265_fieldt("inter_ref_pic_set_prediction_flag", rps->inter_ref_pic_set_prediction_flag);
    h265_fieldt("st_rps_num_negative_pics", rps->num_negative_pics);
    h265_fieldt("st_rps_num_positive_pics", rps->num_positive_pics);
    h265_fieldt("st_rps_num_delta_pocs", rps->num_delta_pocs);
    for (i = 0; i < rps->num_delta_pocs; i++) {
        h265_fieldt("st_rps_poc[%d]", i, s->poc + rps->delta_poc[i]);
        h265_fieldt("st_rps_used[%d]", i, rps->used[i]);
    }
}

static void h265_print_lt_rps(struct hevc_long_term_rps *rps)
{
    (void)rps;
}

static void h265_print_vui(struct hevc_sps *sps, struct hevc_vui *vui)
{
    h265_header("VUI parameters:");
    h265_fieldt("aspect_ratio_info_present_flag", vui->aspect_ratio_info_present_flag);
    h265_fieldt("aspect_ratio_idc", vui->aspect_ratio_idc);
    h265_fieldt("sar_width", vui->sar_width);
    h265_fieldt("sar_height", vui->sar_height);
    h265_fieldt("overscan_info_present_flag", vui->overscan_info_present_flag);
    if (vui->overscan_info_present_flag)
        h265_fieldt("overscan_appropriate_flag", vui->overscan_appropriate_flag);

    h265_fieldt("video_signal_type_present_flag", vui->video_signal_type_present_flag);
    h265_fieldt("video_format", vui->video_format);
    h265_fieldt("video_full_range_flag", vui->video_full_range_flag);

    h265_fieldt("colour_description_present_flag",vui->colour_description_present_flag);
    h265_fieldt("colour_primaries", vui->colour_primaries);
    h265_fieldt("transfer_characteristics", vui->transfer_characteristics);
    h265_fieldt("matrix_coefficients", vui->matrix_coefficients);
    h265_fieldt("chroma_loc_info_present_flag", vui->chroma_loc_info_present_flag);
    h265_fieldt("chroma_sample_loc_type_top_field", vui->chroma_sample_loc_type_top_field);
    h265_fieldt("chroma_sample_loc_type_bottom_field", vui->chroma_sample_loc_type_bottom_field);

    h265_fieldt("neutral_chroma_indication_flag", vui->neutral_chroma_indication_flag);
    h265_fieldt("field_seq_flag", vui->field_seq_flag);
    h265_fieldt("frame_field_info_present_flag", vui->frame_field_info_present_flag);

    h265_fieldt("default_display_window_flag", vui->default_display_window_flag);
    if (vui->default_display_window_flag) {
        h265_fieldt("def_disp_win_left_offset", vui->def_disp_win_left_offset);
        h265_fieldt("def_disp_win_right_offset", vui->def_disp_win_right_offset);
        h265_fieldt("def_disp_win_top_offset", vui->def_disp_win_top_offset);
        h265_fieldt("def_disp_win_bottom_offset", vui->def_disp_win_bottom_offset);
    }

    h265_fieldt("vui_timing_info_present_flag", vui->vui_timing_info_present_flag);
    if (vui->vui_timing_info_present_flag) {
        h265_fieldt("vui_num_units_in_tick", vui->vui_num_units_in_tick);
        h265_fieldt("vui_time_scale", vui->vui_time_scale);
        h265_fieldt("vui_poc_proportional_to_timing_flag", vui->vui_poc_proportional_to_timing_flag);
        if (vui->vui_poc_proportional_to_timing_flag)
            h265_fieldt("vui_num_ticks_poc_diff_one_minus1", vui->vui_num_ticks_poc_diff_one_minus1);
        h265_fieldt("vui_hrd_parameters_present_flag", vui->vui_hrd_parameters_present_flag);
        if (vui->vui_hrd_parameters_present_flag)
            h265_print_hdr(&sps->hdr, 1, sps->max_sub_layers);
    }

    h265_fieldt("bitstream_restriction_flag", vui->bitstream_restriction_flag);
    h265_fieldt("tiles_fixed_structure_flag", vui->tiles_fixed_structure_flag);
    h265_fieldt("motion_vectors_over_pic_boundaries_flag", vui->motion_vectors_over_pic_boundaries_flag);
    if (vui->bitstream_restriction_flag)
        h265_fieldt("restricted_ref_pic_lists_flag", vui->restricted_ref_pic_lists_flag);
    h265_fieldt("min_spatial_segmentation_idc", vui->min_spatial_segmentation_idc);
    h265_fieldt("max_bytes_per_pic_denom", vui->max_bytes_per_pic_denom);
    h265_fieldt("max_bits_per_min_cu_denom", vui->max_bits_per_min_cu_denom);
    h265_fieldt("log2_max_mv_length_horizontal", vui->log2_max_mv_length_horizontal);
    h265_fieldt("log2_max_mv_length_vertical", vui->log2_max_mv_length_vertical);
}

static void h265_print_sps_extensions(struct hevc_sps *sps)
{
    (void)sps;
}

void h265_print_nal_sps(struct hevc_sps *sps)
{
    int i;

    h265_field("sps_video_parameter_set_id", sps->sps_video_parameter_set_id);
    h265_field("sps_temporal_id_nesting_flag", sps->sps_temporal_id_nesting_flag);
    h265_field("max_sub_layers", sps->max_sub_layers);
    h265_field("sps_temporal_id_nesting_flag", sps->sps_temporal_id_nesting_flag);
    h265_print_ptl(&sps->ptl, sps->max_sub_layers);
    h265_field("sps_seq_parameter_set_id", sps->sps_seq_parameter_set_id);
    h265_field("chroma_format_idc", sps->chroma_format_idc);
    h265_field("separate_colour_plane_flag", sps->separate_colour_plane_flag);

    h265_field("pic_width_in_luma_samples", sps->pic_width_in_luma_samples);
    h265_field("pic_height_in_luma_samples", sps->pic_height_in_luma_samples);
    h265_field("conformance_window_flag", sps->conformance_window_flag);
    if (sps->conformance_window_flag) {
        h265_field("conf_win_left_offset", sps->conf_win_left_offset);
        h265_field("conf_win_right_offset", sps->conf_win_right_offset);
        h265_field("conf_win_top_offset", sps->conf_win_top_offset);
        h265_field("conf_win_bottom_offset", sps->conf_win_bottom_offset);
    }

    h265_field("bit_depth_luma_minus8", sps->bit_depth-8);
    h265_field("bit_depth_chroma_minus8", sps->bit_depth_chroma-8);
    h265_field("log2_max_pic_order_cnt_lsb", sps->log2_max_poc_lsb);

    h265_field("sps_sub_layer_ordering_info_present_flag", sps->sps_sub_layer_ordering_info_present_flag);
    for (i = 0; i < sps->max_sub_layers; i++) {
        h265_field("sps_max_dec_pic_buffering[%d]", i, sps->sps_max_dec_pic_buffering[i]);
        h265_field("sps_max_num_reorder_pics[%d]", i, sps->sps_max_num_reorder_pics[i]);
        h265_field("sps_max_latency_increase[%d]", i, sps->sps_max_latency_increase[i]);
    }

    h265_field("log2_min_cb_size", sps->log2_min_cb_size);
    h265_field("log2_diff_max_min_coding_block_size", sps->log2_diff_max_min_coding_block_size);
    h265_field("log2_min_tb_size", sps->log2_min_tb_size);
    h265_field("log2_diff_max_min_transform_block_size", sps->log2_diff_max_min_transform_block_size);
    h265_field("max_transform_hierarchy_depth_inter", sps->max_transform_hierarchy_depth_inter);
    h265_field("max_transform_hierarchy_depth_intra", sps->max_transform_hierarchy_depth_intra);

    h265_field("scaling_list_enable_flag", sps->scaling_list_enable_flag);
    if (sps->scaling_list_enable_flag) {
        h265_field("sps_scaling_list_data_present_flag", sps->sps_scaling_list_data_present_flag);
        h265_print_scaling_list(&sps->scaling_list, "seq");
    }

    h265_field("amp_enabled_flag", sps->amp_enabled_flag);
    h265_field("sample_adaptive_offset_enabled_flag", sps->sample_adaptive_offset_enabled_flag);
    h265_field("pcm_enabled_flag", sps->pcm_enabled_flag);
    if (sps->pcm_enabled_flag) {
        h265_field("pcm_sample_bit_depth_luma_minus1", sps->pcm_sample_bit_depth_luma-1);
        h265_field("pcm_sample_bit_depth_chroma_minus1", sps->pcm_sample_bit_depth_chroma-1);
        h265_field("log2_min_pcm_luma_coding_block_size_minus3", sps->log2_min_pcm_cb_size-3);
        h265_field("log2_diff_max_min_pcm_luma_coding_block_size", sps->log2_max_pcm_cb_size-sps->log2_min_pcm_cb_size);
        h265_field("pcm_loop_filter_disabled_flag", sps->pcm_loop_filter_disabled_flag);
    }

    h265_field("num_short_term_ref_pic_sets", sps->num_short_term_ref_pic_sets);
    for (i = 0; i < sps->num_short_term_ref_pic_sets; i++) {
    }
    h265_field("long_term_ref_pics_present_flag", sps->long_term_ref_pics_present_flag);
    if (sps->long_term_ref_pics_present_flag) {
        h265_field("num_long_term_ref_pics_sps", sps->num_long_term_ref_pics_sps);
        for (i = 0; i < sps->num_long_term_ref_pics_sps; i++) {
            h265_field("lt_ref_pic_poc_lsb_sps[%d]", i, sps->lt_ref_pic_poc_lsb_sps[i]);
            h265_field("used_by_curr_pic_lt_sps_flag[%d]", i, sps->used_by_curr_pic_lt_sps_flag[i]);
        }
    }

    h265_field("sps_temporal_mvp_enabled_flag", sps->sps_temporal_mvp_enabled_flag);
    h265_field("sps_strong_intra_smoothing_enable_flag", sps->sps_strong_intra_smoothing_enable_flag);

    h265_field("vui_parameters_present_flag", sps->vui_parameters_present_flag);
    if (sps->vui_parameters_present_flag)
        h265_print_vui(sps, &sps->vui);

    h265_field("sps_extension_present_flag", sps->sps_extension_present_flag);
    if (sps->sps_extension_present_flag)
        h265_print_sps_extensions(sps);
}

static void h265_print_pps_range_extension(struct hevc_pps *pps)
{
    int i;

    if (pps->transform_skip_enabled_flag)
        h265_field("log2_max_transform_skip_block_size", pps->log2_max_transform_skip_block_size);
    h265_field("cross_component_prediction_enabled_flag", pps->cross_component_prediction_enabled_flag);
    h265_field("chroma_qp_offset_list_enabled_flag", pps->chroma_qp_offset_list_enabled_flag);
    if (pps->chroma_qp_offset_list_enabled_flag) {
        h265_field("diff_cu_chroma_qp_offset_depth", pps->diff_cu_chroma_qp_offset_depth);
        h265_field("chroma_qp_offset_list_len_minus1", pps->chroma_qp_offset_list_len_minus1);
        for (i = 0; i <= pps->chroma_qp_offset_list_len_minus1; i++) {
            h265_field("cb_qp_offset_list[%d]", i, pps->cb_qp_offset_list[i]);
            h265_field("cr_qp_offset_list[%d]", i, pps->cr_qp_offset_list[i]);
        }
    }
    h265_field("log2_sao_offset_scale_luma", pps->log2_sao_offset_scale_luma);
    h265_field("log2_sao_offset_scale_chroma", pps->log2_sao_offset_scale_chroma);
}

void h265_print_nal_pps(struct hevc_pps *pps)
{
    int i;

    h265_field("pps_pic_parameter_set_id", pps->pps_pic_parameter_set_id);
    h265_field("pps_seq_parameter_set_id", pps->sps_id);

    h265_field("dependent_slice_segments_enabled_flag", pps->dependent_slice_segments_enabled_flag);
    h265_field("output_flag_present_flag", pps->output_flag_present_flag);
    h265_field("num_extra_slice_header_bits", pps->num_extra_slice_header_bits);
    h265_field("sign_data_hiding_enabled_flag", pps->sign_data_hiding_enabled_flag);
    h265_field("cabac_init_present_flag", pps->cabac_init_present_flag);

    h265_field("num_ref_idx_l0_default_active_minus1", pps->num_ref_idx_l0_default_active-1);
    h265_field("num_ref_idx_l1_default_active_minus1", pps->num_ref_idx_l1_default_active-1);

    h265_field("pic_init_qp_minus26", pps->pic_init_qp_minus26);
    h265_field("constrained_intra_pred_flag", pps->constrained_intra_pred_flag);
    h265_field("transform_skip_enabled_flag", pps->transform_skip_enabled_flag);
    h265_field("cu_qp_delta_enabled_flag", pps->cu_qp_delta_enabled_flag);
    h265_field("diff_cu_qp_delta_depth", pps->diff_cu_qp_delta_depth);
    h265_field("pps_cb_qp_offset", pps->pps_cb_qp_offset);
    h265_field("pps_cr_qp_offset", pps->pps_cr_qp_offset);
    h265_field("pps_slice_chroma_qp_offsets_present_flag", pps->pps_slice_chroma_qp_offsets_present_flag);

    h265_field("weighted_pred_flag", pps->weighted_pred_flag);
    h265_field("weighted_bipred_flag", pps->weighted_bipred_flag);

    h265_field("transquant_bypass_enabled_flag", pps->transquant_bypass_enabled_flag);
    h265_field("tiles_enabled_flag", pps->tiles_enabled_flag);
    h265_field("entropy_coding_sync_enabled_flag", pps->entropy_coding_sync_enabled_flag);
    h265_field("num_tile_columns", pps->num_tile_columns); // print anyway
    h265_field("num_tile_rows", pps->num_tile_rows); // ""
    if (pps->tiles_enabled_flag) {
        h265_field("uniform_spacing_flag", pps->uniform_spacing_flag);
        for (i = 0; i < pps->num_tile_columns; i++)
            h265_field("column_width[%d]", i, pps->column_width[i]);
        for (i = 0; i < pps->num_tile_rows; i++)
            h265_field("row_height[%d]", i, pps->row_height[i]);
        h265_field("loop_filter_across_tiles_enabled_flag", pps->loop_filter_across_tiles_enabled_flag);
    }
    h265_field("pps_loop_filter_across_slices_enabled_flag", pps->pps_loop_filter_across_slices_enabled_flag);

    h265_field("deblocking_filter_control_present_flag", pps->deblocking_filter_control_present_flag);
    if (pps->deblocking_filter_control_present_flag) {
        h265_field("deblocking_filter_override_enabled_flag", pps->deblocking_filter_override_enabled_flag);
        h265_field("pps_deblocking_filter_disabled_flag", pps->pps_deblocking_filter_disabled_flag);
        if (!pps->pps_deblocking_filter_disabled_flag) {
            h265_field("pps_beta_offset_div2", pps->pps_beta_offset / 2);
            h265_field("pps_tc_offset_div2", pps->pps_tc_offset / 2);
        }
    }

    h265_field("pps_scaling_list_data_present_flag", pps->pps_scaling_list_data_present_flag);
    if (pps->pps_scaling_list_data_present_flag)
        h265_print_scaling_list(&pps->scaling_list, "pic");

    h265_field("lists_modification_present_flag", pps->lists_modification_present_flag);
    h265_field("log2_parallel_merge_level", pps->log2_parallel_merge_level);
    h265_field("slice_segment_header_extension_present_flag", pps->slice_segment_header_extension_present_flag);
    h265_field("pps_extension_present_flag", pps->pps_extension_present_flag);
    if (pps->pps_extension_present_flag) {
        h265_field("pps_range_extension_flag", pps->pps_range_extension_flag);
        h265_field("pps_multilayer_extension_flag", pps->pps_multilayer_extension_flag);
        h265_field("pps_3d_extension_flag", pps->pps_3d_extension_flag);
        h265_field("pps_scc_extension_flag", pps->pps_scc_extension_flag);
        if (pps->pps_range_extension_flag)
            h265_print_pps_range_extension(pps);
    }
}

static void h265_print_pred_weight_table(struct hevc_slice_header *sh)
{
    int i;

    h265_field("has_chroma_weights", sh->has_chroma_weights);
    h265_field("luma_log2_weight_denom", sh->luma_log2_weight_denom);
    h265_field("chroma_log2_weight_denom", sh->chroma_log2_weight_denom);

    for (i = 0; i < sh->num_ref_idx_l0_active; i++) {
        h265_field("luma_weight_l0_flag[%d]", i, sh->luma_weight_l0_flag[i]);
        if (sh->luma_weight_l0_flag[i]) {
            h265_field("luma_weight_l0[%d]", i, sh->luma_weight_l0[i]);
            h265_field("luma_offset_l0[%d]", i, sh->luma_offset_l0[i]);
        }

        h265_field("chroma_weight_l0_flag[%d]", i, sh->chroma_weight_l0_flag[i]);
        if (sh->chroma_weight_l0_flag[i]) {
        // No I can't get the fucking macro to work
        h265_field("chroma_weight_l0[%d][0]", i, sh->chroma_weight_l0[i][0]);
        h265_field("chroma_offset_l0[%d][0]", i, sh->chroma_offset_l0[i][0]);
        h265_field("chroma_weight_l0[%d][1]", i, sh->chroma_weight_l0[i][1]);
        h265_field("chroma_offset_l0[%d][1]", i, sh->chroma_offset_l0[i][1]);
        }
    }

    if (sh->slice_type == HEVC_SLICE_B) {
        for (i = 0; i < sh->num_ref_idx_l1_active; i++) {
            h265_field("luma_weight_l1_flag[%d]", i, sh->luma_weight_l1_flag[i]);
            if (sh->luma_weight_l1_flag[i]) {
                h265_field("luma_weight_l1[%d]", i, sh->luma_weight_l1[i]);
                h265_field("luma_offset_l1[%d]", i, sh->luma_offset_l1[i]);
            }

            h265_field("chroma_weight_l1_flag[%d]", i, sh->chroma_weight_l1_flag[i]);
            if (sh->chroma_weight_l1_flag[i]) {
                h265_field("chroma_weight_l1[%d][0]", i, sh->chroma_weight_l1[i][0]);
                h265_field("chroma_offset_l1[%d][0]", i, sh->chroma_offset_l1[i][0]);
                h265_field("chroma_weight_l1[%d][1]", i, sh->chroma_weight_l1[i][1]);
                h265_field("chroma_offset_l1[%d][1]", i, sh->chroma_offset_l1[i][1]);
            }
        }
    }
}

void h265_print_nal_slice_header(struct h265_context *s, struct hevc_slice_header *sh)
{
    struct hevc_pps *pps = &s->pps_list[sh->pps_id];
    struct hevc_sps *sps = &s->sps_list[pps->sps_id];
    int i;

    h265_field("first_slice_segment_in_pic_flag", sh->first_slice_segment_in_pic_flag);
    h265_field("no_output_of_prior_pics_flag", sh->no_output_of_prior_pics_flag);
    h265_field("slice_pic_parameter_set_id", sh->pps_id);

    h265_field("dependent_slice_segment_flag", sh->dependent_slice_segment_flag);
    if (!sh->first_slice_segment_in_pic_flag)
        h265_field("slice_segment_address", sh->slice_segment_address);

    if (!sh->dependent_slice_segment_flag) {
        h265_field("slice_type", sh->slice_type);
        h265_field("pic_output_flag", sh->pic_output_flag);
        if (sps->separate_colour_plane_flag)
            h265_field("colour_plane_id", sh->colour_plane_id);

        h265_field("pic_order_cnt_lsb", sh->pic_order_cnt_lsb);
        h265_field("pic_order_cnt", s->poc);
        h265_field("short_term_ref_pic_set_sps_flag", sh->short_term_ref_pic_set_sps_flag);
        h265_field("short_term_ref_pic_set_idx", sh->short_term_ref_pic_set_idx);
        if (!IS_IDR(s)) {
            h265_print_st_rps(s, (struct hevc_short_term_rps *)sh->short_term_rps);
            h265_field("short_term_ref_pic_set_size", sh->short_term_ref_pic_set_size);
            h265_print_lt_rps(&sh->long_term_rps);
            h265_field("long_term_ref_pic_set_size", sh->long_term_ref_pic_set_size);
        }
        h265_field("slice_temporal_mvp_enabled_flag", sh->slice_temporal_mvp_enabled_flag);

        h265_field("slice_sao_luma_flag", sh->slice_sao_luma_flag);
        h265_field("slice_sao_chroma_flag", sh->slice_sao_chroma_flag);

        if (sh->slice_type == HEVC_SLICE_P || sh->slice_type == HEVC_SLICE_B) {
            h265_field("num_ref_idx_active_override_flag", sh->num_ref_idx_active_override_flag);
            h265_field("num_ref_idx_l0_active_minus1", sh->num_ref_idx_l0_active-1);
            if (sh->slice_type == HEVC_SLICE_B)
                h265_field("num_ref_idx_l1_active_minus1", sh->num_ref_idx_l1_active-1);
            h265_field("ref_pic_list_modification_flag_l0", sh->ref_pic_list_modification_flag_l0);
            if (sh->slice_type == HEVC_SLICE_B) {
                h265_field("ref_pic_list_modification_flag_l1", sh->ref_pic_list_modification_flag_l1);
                h265_field("mvd_l1_zero_flag", sh->mvd_l1_zero_flag);
            }

            h265_field("cabac_init_flag", sh->cabac_init_flag);
            h265_field("collocated_ref_idx", sh->collocated_ref_idx);
            if (sh->slice_temporal_mvp_enabled_flag)
                h265_field("collocated_from_l0_flag", sh->collocated_from_l0_flag);

            h265_field("has_luma_weights", sh->has_luma_weights);
            if (sh->has_luma_weights)
                h265_print_pred_weight_table(sh);

            h265_field("max_num_merge_cand", sh->max_num_merge_cand);
            h265_field("use_integer_mv_flag", sh->use_integer_mv_flag);
        }

        h265_field("slice_qp_delta", sh->slice_qp_delta);
        h265_field("slice_cb_qp_offset", sh->slice_cb_qp_offset);
        h265_field("slice_cr_qp_offset", sh->slice_cr_qp_offset);
        h265_field("slice_act_y_qp_offset", sh->slice_act_y_qp_offset);
        h265_field("slice_act_cb_qp_offset", sh->slice_act_cb_qp_offset);
        h265_field("slice_act_cr_qp_offset", sh->slice_act_cr_qp_offset);
        h265_field("cu_chroma_qp_offset_enabled_flag", sh->cu_chroma_qp_offset_enabled_flag);

        h265_field("deblocking_filter_override_flag", sh->deblocking_filter_override_flag);
        h265_field("slice_deblocking_filter_disabled_flag", sh->slice_deblocking_filter_disabled_flag);
        h265_field("slice_beta_offset_div2", sh->slice_beta_offset / 2);
        h265_field("slice_tc_offset_div2", sh->slice_tc_offset / 2);

        h265_field("slice_loop_filter_across_slices_enabled_flag", sh->slice_loop_filter_across_slices_enabled_flag);
    }

    if (pps->tiles_enabled_flag || pps->entropy_coding_sync_enabled_flag) {
        h265_field("num_entry_point_offsets", sh->num_entry_point_offsets);
        for (i = 0; i < sh->num_entry_point_offsets; i++)
            h265_field("entry_point_offset[%d]", i, sh->entry_point_offset[i]);
    }
}
