/*
 * Copyright 2023 Eileen Yoon <eyn@gmx.com>
 *
 * From libavcodec
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

#include "bs.h"
#include "hevc.h"

struct hevc_sublayer_hdr_params {
    uint32_t bit_rate_value_minus1[HEVC_MAX_CPB_CNT];
    uint32_t cpb_size_value_minus1[HEVC_MAX_CPB_CNT];
    uint32_t cpb_size_du_value_minus1[HEVC_MAX_CPB_CNT];
    uint32_t bit_rate_du_value_minus1[HEVC_MAX_CPB_CNT];
    uint8_t cbr_flag[HEVC_MAX_CPB_CNT];
};

struct hevc_hdr_params {
    uint8_t nal_hrd_parameters_present_flag;
    uint8_t vcl_hrd_parameters_present_flag;

    uint8_t sub_pic_hrd_params_present_flag;
    uint8_t tick_divisor_minus2;
    uint8_t du_cpb_removal_delay_increment_length_minus1;
    uint8_t sub_pic_cpb_params_in_pic_timing_sei_flag;
    uint8_t dpb_output_delay_du_length_minus1;

    uint8_t bit_rate_scale;
    uint8_t cpb_size_scale;
    uint8_t cpb_size_du_scale;

    uint8_t initial_cpb_removal_delay_length_minus1;
    uint8_t au_cpb_removal_delay_length_minus1;
    uint8_t dpb_output_delay_length_minus1;

    uint8_t fixed_pic_rate_general_flag[HEVC_MAX_SUB_LAYERS];
    uint8_t fixed_pic_rate_within_cvs_flag[HEVC_MAX_SUB_LAYERS];
    uint16_t elemental_duration_in_tc_minus1[HEVC_MAX_SUB_LAYERS];
    uint8_t low_delay_hrd_flag[HEVC_MAX_SUB_LAYERS];
    uint8_t cpb_cnt_minus1[HEVC_MAX_SUB_LAYERS];

    struct hevc_sublayer_hdr_params nal_params[HEVC_MAX_SUB_LAYERS];
    struct hevc_sublayer_hdr_params vcl_params[HEVC_MAX_SUB_LAYERS];
};

struct hevc_ptl_common {
    uint8_t profile_space;
    uint8_t tier_flag;
    uint8_t profile_idc;
    uint8_t profile_compatibility_flag[32];
    uint8_t progressive_source_flag;
    uint8_t interlaced_source_flag;
    uint8_t non_packed_constraint_flag;
    uint8_t frame_only_constraint_flag;
    uint8_t max_12bit_constraint_flag;
    uint8_t max_10bit_constraint_flag;
    uint8_t max_8bit_constraint_flag;
    uint8_t max_422chroma_constraint_flag;
    uint8_t max_420chroma_constraint_flag;
    uint8_t max_monochrome_constraint_flag;
    uint8_t intra_constraint_flag;
    uint8_t one_picture_only_constraint_flag;
    uint8_t lower_bit_rate_constraint_flag;
    uint8_t max_14bit_constraint_flag;
    uint8_t inbld_flag;
    uint8_t level_idc;
};

struct hevc_ptl {
    struct hevc_ptl_common general_ptl;
    struct hevc_ptl_common sub_layer_ptl[HEVC_MAX_SUB_LAYERS];

    uint8_t sub_layer_profile_present_flag[HEVC_MAX_SUB_LAYERS];
    uint8_t sub_layer_level_present_flag[HEVC_MAX_SUB_LAYERS];
};

struct hevc_vps {
    unsigned int vps_id; /* vps_video_parameter_set_id */

    uint8_t vps_base_layer_internal_flag;
    uint8_t vps_base_layer_available_flag;
    uint32_t vps_max_layers; /* vps_max_layers_minus1 */
    uint32_t vps_max_sub_layers; /* vps_max_sub_layers_minus1 */
    uint8_t vps_temporal_id_nesting_flag;
    struct hevc_ptl ptl;

    uint8_t vps_sub_layer_ordering_info_present_flag;
    uint32_t vps_max_dec_pic_buffering[HEVC_MAX_SUB_LAYERS]; /* vps_max_dec_pic_buffering_minus1 */
    uint8_t vps_max_num_reorder_pics[HEVC_MAX_SUB_LAYERS];
    uint32_t vps_max_latency_increase[HEVC_MAX_SUB_LAYERS]; /* vps_max_latency_increase_plus1 */
    uint8_t vps_max_layer_id;
    uint32_t vps_num_layer_sets; /* vps_num_layer_sets_minus1 */

    uint8_t vps_timing_info_present_flag;
    uint32_t vps_num_units_in_tick;
    uint32_t vps_time_scale;
    uint8_t vps_poc_proportional_to_timing_flag;
    uint32_t vps_num_ticks_poc_diff_one; /* vps_num_ticks_poc_diff_one_minus1 */
    uint16_t vps_num_hrd_parameters;
    uint16_t hrd_layer_set_idx[HEVC_MAX_LAYER_SETS];
    uint8_t cprms_present_flag[HEVC_MAX_LAYER_SETS];
    struct hevc_hdr_params hdr[HEVC_MAX_LAYER_SETS];
};

struct hevc_short_term_rps {
    uint8_t inter_ref_pic_set_prediction_flag;
    uint32_t delta_idx; /* delta_idx_minus1 */
    uint8_t use_delta_flag;
    uint8_t delta_rps_sign;
    uint32_t abs_delta_rps;
    uint32_t num_negative_pics;
    uint32_t num_positive_pics;
    int num_delta_pocs;
    int rps_idx_num_delta_pocs;
    int32_t delta_poc_s0[32];
    int32_t delta_poc_s1[32];
    int32_t delta_poc[32];
    uint8_t used[32];
};

typedef struct ScalingList {
    /* This is a little wasteful, since sizeID 0 only needs 8 coeffs,
     * and size ID 3 only has 2 arrays, not 6. */
    uint8_t sl[4][6][64];
    uint8_t sl_dc[2][6];
    uint8_t scaling_list_pred_mode_flag[4][6];
    uint8_t scaling_list_pred_matrix_id_delta[4][6];
    //int16_t scaling_list_dc_coef_minus8[4][6];
    //int8_t scaling_list_delta_coeff[4][6][64];
} ScalingList;

struct hevc_vui {
    uint8_t aspect_ratio_info_present_flag;
    uint8_t aspect_ratio_idc;
    uint16_t sar_width;
    uint16_t sar_height;

    uint8_t overscan_info_present_flag;
    uint8_t overscan_appropriate_flag;

    uint8_t video_signal_type_present_flag;
    uint8_t video_format;
    uint8_t video_full_range_flag;
    uint8_t colour_description_present_flag;
    uint8_t colour_primaries;
    uint8_t transfer_characteristics;
    uint8_t matrix_coefficients;

    uint8_t chroma_loc_info_present_flag;
    uint8_t chroma_sample_loc_type_top_field;
    uint8_t chroma_sample_loc_type_bottom_field;

    uint8_t neutral_chroma_indication_flag;
    uint8_t field_seq_flag;
    uint8_t frame_field_info_present_flag;

    uint8_t default_display_window_flag;
    uint16_t def_disp_win_left_offset;
    uint16_t def_disp_win_right_offset;
    uint16_t def_disp_win_top_offset;
    uint16_t def_disp_win_bottom_offset;

    uint8_t vui_timing_info_present_flag;
    uint32_t vui_num_units_in_tick;
    uint32_t vui_time_scale;
    uint8_t vui_poc_proportional_to_timing_flag;
    uint32_t vui_num_ticks_poc_diff_one_minus1;
    uint8_t vui_hrd_parameters_present_flag;
    struct hevc_hdr_params hdr;

    uint8_t bitstream_restriction_flag;
    uint8_t tiles_fixed_structure_flag;
    uint8_t motion_vectors_over_pic_boundaries_flag;
    uint8_t restricted_ref_pic_lists_flag;
    uint16_t min_spatial_segmentation_idc;
    uint8_t max_bytes_per_pic_denom;
    uint8_t max_bits_per_min_cu_denom;
    uint8_t log2_max_mv_length_horizontal;
    uint8_t log2_max_mv_length_vertical;
};

struct hevc_sps {
    uint8_t sps_video_parameter_set_id;
    uint8_t max_sub_layers; /* sps_max_sub_layers_minus1 */
    uint8_t sps_temporal_id_nesting_flag;
    struct hevc_ptl ptl;
    uint8_t sps_seq_parameter_set_id;
    uint8_t chroma_format_idc;
    uint8_t separate_colour_plane_flag;

    uint32_t pic_width_in_luma_samples;
    uint32_t pic_height_in_luma_samples;
    uint8_t conformance_window_flag;
    uint32_t conf_win_left_offset;
    uint32_t conf_win_right_offset;
    uint32_t conf_win_top_offset;
    uint32_t conf_win_bottom_offset;
    uint8_t bit_depth; /* bit_depth_luma_minus8 */
    uint8_t bit_depth_chroma; /* bit_depth_chroma_minus8 */
    uint8_t log2_max_poc_lsb; /* log2_max_pic_order_cnt_lsb_minus4 */

    uint8_t sps_sub_layer_ordering_info_present_flag;
    uint32_t sps_max_dec_pic_buffering[HEVC_MAX_SUB_LAYERS]; /* sps_max_dec_pic_buffering_minus1 */
    uint32_t sps_max_num_reorder_pics[HEVC_MAX_SUB_LAYERS];
    int32_t sps_max_latency_increase[HEVC_MAX_SUB_LAYERS]; /* sps_max_latency_increase_plus1 */

    uint32_t log2_min_cb_size; /* log2_min_luma_coding_block_size_minus3 */
    uint32_t log2_diff_max_min_coding_block_size;
    uint32_t log2_min_tb_size; /* log2_min_luma_transform_block_size_minus2 */
    uint32_t log2_diff_max_min_transform_block_size; /* log2_diff_max_min_luma_transform_block_size */
    uint32_t max_transform_hierarchy_depth_inter;
    uint32_t max_transform_hierarchy_depth_intra;

    uint8_t scaling_list_enable_flag;
    uint8_t sps_scaling_list_data_present_flag;
    ScalingList scaling_list;

    uint8_t amp_enabled_flag;
    uint8_t sample_adaptive_offset_enabled_flag;

    /* pcm */
    uint8_t pcm_enabled_flag;
    uint8_t pcm_sample_bit_depth_luma; /* pcm_sample_bit_depth_luma_minus1 */
    uint8_t pcm_sample_bit_depth_chroma; /* pcm_sample_bit_depth_chroma_minus1 */
    uint32_t log2_min_pcm_cb_size; /* log2_min_pcm_luma_coding_block_size_minus3 */
    uint32_t log2_max_pcm_cb_size; /* log2_max_pcm_luma_coding_block_size_minus3 */
    uint8_t pcm_loop_filter_disabled_flag;

    uint8_t num_short_term_ref_pic_sets;
    struct hevc_short_term_rps st_rps[HEVC_MAX_SHORT_TERM_REF_PIC_SETS];
    uint8_t long_term_ref_pics_present_flag;
    uint8_t num_long_term_ref_pics_sps;
    uint16_t lt_ref_pic_poc_lsb_sps[HEVC_MAX_LONG_TERM_REF_PICS];
    uint8_t used_by_curr_pic_lt_sps_flag[HEVC_MAX_LONG_TERM_REF_PICS];

    uint8_t vui_parameters_present_flag;
    struct hevc_vui vui;
    struct hevc_hdr_params hdr;

    uint8_t sps_temporal_mvp_enabled_flag;
    uint8_t sps_strong_intra_smoothing_enable_flag;

    /* extensions */
    uint8_t sps_extension_present_flag;
    uint8_t sps_range_extension_flag;
    uint8_t sps_multilayer_extension_flag;
    uint8_t sps_3d_extension_flag;
    uint8_t sps_scc_extension_flag;
    uint8_t sps_extension_4bits;

    /* range extension */
    uint8_t transform_skip_rotation_enabled_flag;
    uint8_t transform_skip_context_enabled_flag;
    uint8_t implicit_rdpcm_enabled_flag;
    uint8_t explicit_rdpcm_enabled_flag;
    uint8_t extended_precision_processing_flag;
    uint8_t intra_smoothing_disabled_flag;
    uint8_t high_precision_offsets_enabled_flag;
    uint8_t persistent_rice_adaptation_enabled_flag;
    uint8_t cabac_bypass_alignment_enabled_flag;

    /* multilayer extension */
    uint8_t inter_view_mv_vert_constraint_flag;

    /* 3d extension */
    uint8_t iv_di_mc_enabled_flag[2];
    uint8_t iv_mv_scal_enabled_flag[2];
    uint8_t log2_ivmc_sub_pb_size_minus3[2];
    uint8_t iv_res_pred_enabled_flag;
    uint8_t depth_ref_enabled_flag;
    uint8_t vsp_mc_enabled_flag;
    uint8_t dbbp_enabled_flag;
    uint8_t tex_mc_enabled_flag;
    uint8_t intra_contour_enabled_flag;
    uint8_t intra_dc_only_wedge_enabled_flag;
    uint8_t cqt_cu_part_pred_enabled_flag;
    uint8_t inter_dc_only_enabled_flag;
    uint8_t skip_intra_enabled_flag;

    /* scc extension */
    uint8_t sps_curr_pic_ref_enabled_flag;
    uint8_t palette_mode_enabled_flag;
    uint8_t palette_max_size;
    uint32_t delta_palette_max_predictor_size;
    uint8_t sps_palette_predictor_initializer_present_flag;
    uint32_t sps_num_palette_predictor_initializer; /* sps_num_palette_predictor_initializer_minus1 */
    uint32_t sps_palette_predictor_initializer[3][HEVC_MAX_PALETTE_PREDICTOR_SIZE];
    uint8_t motion_vector_resolution_control_idc;
    uint8_t intra_boundary_filtering_disabled_flag;

    /* derived */
    int width;
    int height;

    int log2_ctb_size;
    int log2_min_pu_size;
    int ctb_width;
    int ctb_height;
    int ctb_size;
    int min_cb_width;
    int min_cb_height;
    int min_tb_width;
    int min_tb_height;
    int min_pu_width;
    int min_pu_height;
    int tb_mask;
    int qp_bd_offset;
};

struct hevc_pps {
    uint8_t pps_pic_parameter_set_id;
    uint8_t sps_id; /* pps_seq_parameter_set_id */

    uint8_t dependent_slice_segments_enabled_flag;
    uint8_t output_flag_present_flag;
    uint8_t num_extra_slice_header_bits;
    uint8_t sign_data_hiding_enabled_flag;
    uint8_t cabac_init_present_flag;

    uint8_t num_ref_idx_l0_default_active; /* num_ref_idx_l0_default_active_minus1 */
    uint8_t num_ref_idx_l1_default_active; /* num_ref_idx_l1_default_active_minus1 */

    int32_t pic_init_qp_minus26;

    uint8_t constrained_intra_pred_flag;
    uint8_t transform_skip_enabled_flag;
    uint8_t cu_qp_delta_enabled_flag;
    uint8_t diff_cu_qp_delta_depth;

    int8_t pps_cb_qp_offset;
    int8_t pps_cr_qp_offset;
    uint8_t pps_slice_chroma_qp_offsets_present_flag;

    uint8_t weighted_pred_flag;
    uint8_t weighted_bipred_flag;

    uint8_t transquant_bypass_enabled_flag;
    uint8_t tiles_enabled_flag;
    uint8_t entropy_coding_sync_enabled_flag;

    uint8_t num_tile_columns;
    uint8_t num_tile_rows;
    uint8_t uniform_spacing_flag;
    uint16_t column_width[HEVC_MAX_TILE_COLUMNS];
    uint16_t row_height[HEVC_MAX_TILE_ROWS];
    uint8_t loop_filter_across_tiles_enabled_flag;

    uint8_t pps_loop_filter_across_slices_enabled_flag;
    uint8_t deblocking_filter_control_present_flag;
    uint8_t deblocking_filter_override_enabled_flag;
    uint8_t pps_deblocking_filter_disabled_flag;
    int32_t pps_beta_offset; /* pps_beta_offset_div2 */
    int32_t pps_tc_offset; /* pps_tc_offset_div2 */

    uint8_t pps_scaling_list_data_present_flag;
    ScalingList scaling_list;

    uint8_t lists_modification_present_flag;
    uint32_t log2_parallel_merge_level; /* log2_parallel_merge_level_minus2 */

    uint8_t slice_segment_header_extension_present_flag;

    uint8_t pps_extension_present_flag;
    uint8_t pps_range_extension_flag;
    uint8_t pps_multilayer_extension_flag;
    uint8_t pps_3d_extension_flag;
    uint8_t pps_scc_extension_flag;
    uint8_t pps_extension_4bits;

    // Range extension.
    uint32_t log2_max_transform_skip_block_size; /* log2_max_transform_skip_block_size_minus2 */
    uint8_t cross_component_prediction_enabled_flag;
    uint8_t chroma_qp_offset_list_enabled_flag;
    uint8_t diff_cu_chroma_qp_offset_depth;
    uint8_t chroma_qp_offset_list_len_minus1;
    int8_t cb_qp_offset_list[6];
    int8_t cr_qp_offset_list[6];
    uint8_t log2_sao_offset_scale_luma;
    uint8_t log2_sao_offset_scale_chroma;

    // Screen content coding extension.
    uint8_t pps_curr_pic_ref_enabled_flag;
    uint8_t residual_adaptive_colour_transform_enabled_flag;
    uint8_t pps_slice_act_qp_offsets_present_flag;
    int32_t pps_act_y_qp_offset; /* pps_act_y_qp_offset_plus5 */
    int32_t pps_act_cb_qp_offset; /* pps_act_cb_qp_offset_plus5 */
    int32_t pps_act_cr_qp_offset; /* pps_act_cr_qp_offset_plus3 */

    uint8_t pps_palette_predictor_initializer_present_flag;
    uint8_t pps_num_palette_predictor_initializer;
    uint8_t monochrome_palette_flag;
    uint32_t luma_bit_depth_entry; /* luma_bit_depth_entry_minus8 */
    uint32_t chroma_bit_depth_entry; /* chroma_bit_depth_entry_minus8 */
    uint16_t pps_palette_predictor_initializer[3][128];
};

struct hevc_long_term_rps {
    int     poc[32];
    uint8_t poc_msb_present[32];
    uint8_t used[32];
    uint8_t nb_refs;
};

struct hevc_slice_header {
    uint8_t first_slice_segment_in_pic_flag;
    uint8_t no_output_of_prior_pics_flag;
    uint8_t pps_id; /* slice_pic_parameter_set_id */

    uint8_t dependent_slice_segment_flag;
    uint16_t slice_segment_address;
    uint8_t slice_reserved_flag[8];
    uint8_t slice_type;
    uint8_t pic_output_flag;
    uint8_t colour_plane_id;

    uint16_t pic_order_cnt_lsb; /* slice_pic_order_cnt_lsb */
    uint8_t short_term_ref_pic_set_sps_flag;
    struct hevc_short_term_rps slice_rps;
    const struct hevc_short_term_rps *short_term_rps;
    uint8_t short_term_ref_pic_set_idx;
    struct hevc_long_term_rps long_term_rps;
    uint8_t slice_temporal_mvp_enabled_flag;

    uint8_t slice_sao_luma_flag;
    uint8_t slice_sao_chroma_flag;

    uint8_t num_ref_idx_active_override_flag;
    uint16_t num_ref_idx_l0_active; /* num_ref_idx_l0_active_minus1 */
    uint16_t num_ref_idx_l1_active; /* num_ref_idx_l1_active_minus1 */

    uint8_t ref_pic_list_modification_flag_l0;
    uint8_t list_entry_lx[2][HEVC_MAX_REFS];
    uint8_t ref_pic_list_modification_flag_l1;
    //uint8_t list_entry_l1[HEVC_MAX_REFS];

    uint8_t mvd_l1_zero_flag;
    uint8_t cabac_init_flag;
    uint8_t collocated_from_l0_flag;
    uint8_t collocated_ref_idx;

    /* pred weights */
    uint8_t luma_log2_weight_denom;
    int64_t delta_chroma_log2_weight_denom;
    uint8_t chroma_log2_weight_denom; /* derived */

    uint8_t luma_weight_l0_flag[HEVC_MAX_REFS];
    uint8_t chroma_weight_l0_flag[HEVC_MAX_REFS];
    int8_t delta_luma_weight_l0[HEVC_MAX_REFS];
    int16_t luma_offset_l0[HEVC_MAX_REFS];
    int16_t luma_weight_l0[HEVC_MAX_REFS]; /* derived */
    int8_t delta_chroma_weight_l0[HEVC_MAX_REFS][2];
    int8_t delta_chroma_offset_l0[HEVC_MAX_REFS][2];
    int16_t chroma_weight_l0[HEVC_MAX_REFS][2]; /* derived */
    int16_t chroma_offset_l0[HEVC_MAX_REFS][2]; /* derived */

    uint8_t luma_weight_l1_flag[HEVC_MAX_REFS];
    uint8_t chroma_weight_l1_flag[HEVC_MAX_REFS];
    int8_t delta_luma_weight_l1[HEVC_MAX_REFS];
    int16_t luma_offset_l1[HEVC_MAX_REFS];
    int16_t luma_weight_l1[HEVC_MAX_REFS]; /* derived */
    int8_t delta_chroma_weight_l1[HEVC_MAX_REFS][2];
    int8_t delta_chroma_offset_l1[HEVC_MAX_REFS][2];
    int16_t chroma_weight_l1[HEVC_MAX_REFS][2]; /* derived */
    int16_t chroma_offset_l1[HEVC_MAX_REFS][2]; /* derived */

    int32_t max_num_merge_cand; /* five_minus_max_num_merge_cand */
    uint8_t use_integer_mv_flag;

    int8_t slice_qp_delta;
    int8_t slice_cb_qp_offset;
    int8_t slice_cr_qp_offset;
    int8_t slice_act_y_qp_offset;
    int8_t slice_act_cb_qp_offset;
    int8_t slice_act_cr_qp_offset;
    uint8_t cu_chroma_qp_offset_enabled_flag;

    uint8_t deblocking_filter_override_flag;
    uint8_t slice_deblocking_filter_disabled_flag;
    int32_t slice_beta_offset; /* slice_beta_offset_div2 */
    int32_t slice_tc_offset; /* slice_tc_offset_div2 */
    uint8_t slice_loop_filter_across_slices_enabled_flag;

    uint16_t num_entry_point_offsets;
    uint8_t offset_len; /* offset_len_minus1 */
    uint32_t entry_point_offset[HEVC_MAX_ENTRY_POINT_OFFSETS]; /* entry_point_offset_minus1 */

    /* derived */
    unsigned int short_term_ref_pic_set_size;
    unsigned int long_term_ref_pic_set_size;
    unsigned int nb_refs[2];
    int rpl_modification_flag[2];
    int has_luma_weights;
    int has_chroma_weights;
};

struct h265_context {
    struct bitstream gb;
    int nal_unit_type;
    int nuh_layer_id;
    int temporal_id;
    struct hevc_vps vps_list[HEVC_MAX_VPS_COUNT];
    struct hevc_sps sps_list[HEVC_MAX_SPS_COUNT];
    struct hevc_pps pps_list[HEVC_MAX_PPS_COUNT];
    struct hevc_slice_header sh; /* active slice */

    struct hevc_vps tmp_vps; // just we don't have to alloc again
	struct hevc_sps tmp_sps;
    struct hevc_pps tmp_pps;

    int poc;
    int pocTid0;
    int slice_idx; ///< number of the slice being currently decoded
    int eos;       ///< current packet contains an EOS/EOB NAL
    int last_eos;  ///< last packet contains an EOS/EOB NAL
    int max_ra;
    int bs_width;
    int bs_height;
    int overlap;
};

#define L0 0
#define L1 1
#define IS_IDR(s) ((s)->nal_unit_type == HEVC_NAL_IDR_W_RADL || (s)->nal_unit_type == HEVC_NAL_IDR_N_LP)
#define IS_BLA(s) ((s)->nal_unit_type == HEVC_NAL_BLA_W_RADL || (s)->nal_unit_type == HEVC_NAL_BLA_W_LP || \
                   (s)->nal_unit_type == HEVC_NAL_BLA_N_LP)
#define IS_IRAP(s) ((s)->nal_unit_type >= HEVC_NAL_BLA_W_LP && (s)->nal_unit_type <= HEVC_NAL_RSV_IRAP_VCL23)

int h265_decode_nal_unit(struct h265_context *ctx, uint8_t *buf, int size);

#endif /* __H265_H__ */
