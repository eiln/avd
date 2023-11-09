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

#ifndef __H264_H__
#define __H264_H__

#include "bs.h"

enum h264_nal_unit_type {
	H264_NAL_SLICE_NONIDR = 1,
	H264_NAL_SLICE_PART_A = 2, /* main data */
	H264_NAL_SLICE_PART_B = 3, /* I, SI residual blocks */
	H264_NAL_SLICE_PART_C = 4, /* P, B residual blocks */
	H264_NAL_SLICE_IDR = 5,
	H264_NAL_SEI = 6,
	H264_NAL_SEQPARM = 7,
	H264_NAL_PICPARM = 8,
	H264_NAL_ACC_UNIT_DELIM = 9,
	H264_NAL_END_SEQ = 10,
	H264_NAL_END_STREAM = 11,
	H264_NAL_FILLER_DATA = 12,
	H264_NAL_SEQPARM_EXT = 13,
	H264_NAL_PREFIX_NAL_UNIT = 14, /* SVC/MVC */
	H264_NAL_SUBSET_SEQPARM = 15, /* SVC/MVC */
	H264_NAL_SLICE_AUX = 19,
	H264_NAL_SLICE_EXT = 20, /* SVC/MVC */
};

enum h264_profile_idc {
	H264_PROFILE_CAVLC_444 = 44,
	H264_PROFILE_BASELINE = 66,
	H264_PROFILE_MAIN = 77,
	H264_PROFILE_SCALABLE_BASELINE = 83,
	H264_PROFILE_SCALABLE_HIGH = 86,
	H264_PROFILE_EXTENDED = 88,
	H264_PROFILE_HIGH = 100,
	H264_PROFILE_HIGH_10 = 110,
	H264_PROFILE_MULTIVIEW_HIGH = 118,
	H264_PROFILE_HIGH_422 = 122,
	H264_PROFILE_STEREO_HIGH = 128,
	H264_PROFILE_HIGH_444 = 144,
	H264_PROFILE_HIGH_444_PRED = 244,
};

enum h264_slice_group_map_type {
	H264_SLICE_GROUP_MAP_INTERLEAVED = 0,
	H264_SLICE_GROUP_MAP_DISPERSED = 1,
	H264_SLICE_GROUP_MAP_FOREGROUND = 2,
	H264_SLICE_GROUP_MAP_CHANGING_BOX = 3,
	H264_SLICE_GROUP_MAP_CHANGING_VERTICAL = 4,
	H264_SLICE_GROUP_MAP_CHANGING_HORIZONTAL = 5,
	H264_SLICE_GROUP_MAP_EXPLICIT = 6,
};

enum h264_primary_pic_type {
	H264_PRIMARY_PIC_TYPE_I = 0,
	H264_PRIMARY_PIC_TYPE_P_I = 1,
	H264_PRIMARY_PIC_TYPE_P_B_I = 2,
	H264_PRIMARY_PIC_TYPE_SI = 3,
	H264_PRIMARY_PIC_TYPE_SP_SI = 4,
	H264_PRIMARY_PIC_TYPE_I_SI = 5,
	H264_PRIMARY_PIC_TYPE_P_I_SP_SI = 6,
	H264_PRIMARY_PIC_TYPE_P_B_I_SP_SI = 7,
};

enum h264_ref_pic_mod { /* modification_of_pic_nums_idc */
	H264_REF_PIC_MOD_PIC_NUM_SUB = 0,
	H264_REF_PIC_MOD_PIC_NUM_ADD = 1,
	H264_REF_PIC_MOD_LONG_TERM = 2,
	H264_REF_PIC_MOD_END = 3,
	/* MVC */
	H264_REF_PIC_MOD_VIEW_IDX_SUB = 4,
	H264_REF_PIC_MOD_VIEW_IDX_ADD = 5,
};

enum h264_mmco_opcode { /* memory_management_control_operation */
	H264_MMCO_END = 0,
	H264_MMCO_FORGET_SHORT = 1,
	H264_MMCO_FORGET_LONG = 2,
	H264_MMCO_SHORT_TO_LONG = 3,
	H264_MMCO_FORGET_LONG_MAX = 4,
	H264_MMCO_FORGET_ALL = 5,
	H264_MMCO_THIS_TO_LONG = 6,
};

enum h264_slice_type {
	H264_SLICE_TYPE_P = 0,
	H264_SLICE_TYPE_B = 1,
	H264_SLICE_TYPE_I = 2,
	H264_SLICE_TYPE_SP = 3,
	H264_SLICE_TYPE_SI = 4,
};

enum {
	// 7.4.2.1.1: seq_parameter_set_id is in [0, 31].
	H264_MAX_SPS_COUNT = 32,
	// 7.4.2.2: pic_parameter_set_id is in [0, 255].
	H264_MAX_PPS_COUNT = 256,

	// A.3: MaxDpbFrames is bounded above by 16.
	H264_MAX_DPB_FRAMES = 16,
	// 7.4.2.1.1: max_num_ref_frames is in [0, MaxDpbFrames], and
	// each reference frame can have two fields.
	H264_MAX_REFS = 2 * H264_MAX_DPB_FRAMES,

	// 7.4.3.1: modification_of_pic_nums_idc is not equal to 3 at most
	// num_ref_idx_lN_active + 1 times (that is, once for each
	// possible reference), then equal to 3 once.
	H264_MAX_RPLM_COUNT = H264_MAX_REFS + 1,

	// 7.4.3.3: in the worst case, we begin with a full short-term
	// reference picture list.  Each picture in turn is moved to the
	// long-term list (type 3) and then discarded from there (type 2).
	// Then, we set the length of the long-term list (type 4), mark
	// the current picture as long-term (type 6) and terminate the
	// process (type 0).
	H264_MAX_MMCO_COUNT = H264_MAX_REFS * 2 + 3,

	// A.2.1, A.2.3: profiles supporting FMO constrain
	// num_slice_groups to be in [0, 7].
	H264_MAX_SLICE_GROUPS = 8,

	// E.2.2: cpb_cnt is in [0, 31].
	H264_MAX_CPB_CNT = 32,

	// A.3: in table A-1 the highest level allows a MaxFS of 139264.
	H264_MAX_MB_PIC_SIZE = 139264,
	// A.3.1, A.3.2: PicWidthInMbs and PicHeightInMbs are constrained
	// to be not greater than sqrt(MaxFS * 8).  Hence height/width are
	// bounded above by sqrt(139264 * 8) = 1055.5 macroblocks.
	H264_MAX_MB_WIDTH = 1055,
	H264_MAX_MB_HEIGHT = 1055,
	H264_MAX_WIDTH = H264_MAX_MB_WIDTH * 16,
	H264_MAX_HEIGHT = H264_MAX_MB_HEIGHT * 16,
};

#define PICT_TOP_FIELD     1
#define PICT_BOTTOM_FIELD  2
#define PICT_FRAME         3
#define FIELD_PICTURE(sl) ((sl)->picture_structure != PICT_FRAME)

struct h264_hrd_parameters {
	uint32_t cpb_cnt;
	uint32_t bit_rate_scale;
	uint32_t cpb_size_scale;
	uint32_t bit_rate_value[32];
	uint32_t cpb_size_value[32];
	uint32_t cbr_flag[32];
	uint32_t initial_cpb_removal_delay_length;
	uint32_t cpb_removal_delay_length;
	uint32_t dpb_output_delay_length;
	uint32_t time_offset_length;
};

struct h264_vui {
	uint32_t aspect_ratio_info_present_flag;
	uint32_t aspect_ratio_idc;
	uint32_t sar_width;
	uint32_t sar_height;
	uint32_t overscan_info_present_flag;
	uint32_t overscan_appropriate_flag;
	uint32_t video_signal_type_present_flag;
	uint32_t video_format;
	uint32_t video_full_range_flag;
	uint32_t colour_description_present_flag;
	uint32_t colour_primaries;
	uint32_t transfer_characteristics;
	uint32_t matrix_coefficients;
	uint32_t chroma_loc_info_present_flag;
	uint32_t chroma_sample_loc_type_top_field;
	uint32_t chroma_sample_loc_type_bottom_field;
	uint32_t timing_info_present_flag;
	uint32_t num_units_in_tick;
	uint32_t time_scale;
	uint32_t fixed_frame_rate_flag;

	int nal_hrd_parameters_flag;
	struct h264_hrd_parameters nal_hrd_parameters;
	int vcl_hrd_parameters_flag;
	struct h264_hrd_parameters vcl_hrd_parameters;

	uint32_t low_delay_hrd_flag;
	uint32_t pic_struct_present_flag;
	uint32_t bitstream_restriction_present_flag;
	uint32_t motion_vectors_over_pic_bounduaries_flag;
	uint32_t max_bytes_per_pic_denom;
	uint32_t max_bits_per_mb_denom;
	uint32_t log2_max_mv_length_horizontal;
	uint32_t log2_max_mv_length_vertical;
	uint32_t num_reorder_frames;
	uint32_t max_dec_frame_buffering;
};

struct h264_sps {
	uint32_t profile_idc;
	uint32_t constraint_set;
	uint32_t level_idc;
	uint32_t seq_parameter_set_id;

	/* new profile only stuff */
	uint32_t chroma_format_idc;
	uint32_t separate_colour_plane_flag;
	uint32_t bit_depth_luma_minus8;
	uint32_t bit_depth_chroma_minus8;
	uint32_t qpprime_y_zero_transform_bypass_flag;
	uint32_t seq_scaling_matrix_present_flag;
	uint32_t seq_scaling_list_present_flag[12];
	uint32_t use_default_scaling_matrix_flag[12];
	uint32_t seq_scaling_list_4x4[6][16];
	uint32_t seq_scaling_list_8x8[6][64];

	uint32_t log2_max_frame_num;
	uint32_t pic_order_cnt_type;
	uint32_t log2_max_pic_order_cnt_lsb;
	uint32_t delta_pic_order_always_zero_flag;
	int32_t offset_for_non_ref_pic;
	int32_t offset_for_top_to_bottom_field;
	uint32_t num_ref_frames_in_pic_order_cnt_cycle;
	int32_t offset_for_ref_frame[255];
	uint32_t max_num_ref_frames;
	uint32_t gaps_in_frame_num_value_allowed_flag;
	uint32_t pic_width_in_mbs;
	uint32_t pic_height_in_map_units;
	uint32_t frame_mbs_only_flag;
	uint32_t mb_adaptive_frame_field_flag;
	uint32_t direct_8x8_inference_flag;
	uint32_t frame_cropping_flag;
	uint32_t frame_crop_left_offset;
	uint32_t frame_crop_right_offset;
	uint32_t frame_crop_top_offset;
	uint32_t frame_crop_bottom_offset;

	int vui_parameters_present_flag;
	struct h264_vui vui;

	/* SVC part */
	int is_svc;
	uint32_t inter_layer_deblocking_filter_control_present_flag;
	uint32_t extended_spatial_scalability_idc;
	uint32_t chroma_phase_x_plus1_flag;
	uint32_t chroma_phase_y_plus1;
	uint32_t seq_ref_layer_chroma_phase_x_plus1_flag;
	uint32_t seq_ref_layer_chroma_phase_y_plus1;
	int32_t seq_ref_layer_left_offset;
	int32_t seq_ref_layer_top_offset;
	int32_t seq_ref_layer_right_offset;
	int32_t seq_ref_layer_bottom_offset;
	uint32_t seq_tcoeff_level_prediction_flag;
	uint32_t adaptive_tcoeff_level_prediction_flag;
	uint32_t slice_header_restriction_flag;
	int svc_vui_parameters_present_flag;
	struct h264_vui svc_vui;

	/* MVC */
	int is_mvc;
	uint32_t num_views;
	struct h264_sps_mvc_view {
		uint32_t view_id;
		uint32_t num_anchor_refs_l0;
		uint32_t anchor_ref_l0[15];
		uint32_t num_anchor_refs_l1;
		uint32_t anchor_ref_l1[15];
		uint32_t num_non_anchor_refs_l0;
		uint32_t non_anchor_ref_l0[15];
		uint32_t num_non_anchor_refs_l1;
		uint32_t non_anchor_ref_l1[15];
	} *views;
	uint32_t num_level_values_signalled;
	struct h264_sps_mvc_level {
		uint32_t level_idc;
		uint32_t num_applicable_ops;
		struct h264_sps_mvc_applicable_op {
			uint32_t temporal_id;
			uint32_t num_target_views;
			uint32_t *target_view_id;
			uint32_t num_views;
		} *applicable_ops;
	} *levels;
	int mvc_vui_parameters_present_flag;
	struct h264_vui mvc_vui;

	/* extension [alpha] part */
	int has_ext;
	uint32_t aux_format_idc;
	uint32_t bit_depth_aux_minus8;
	uint32_t alpha_incr_flag;
	uint32_t alpha_opaque_value;
	uint32_t alpha_transparent_value;
};

struct h264_pps {
	uint32_t pic_parameter_set_id;
	uint32_t seq_parameter_set_id;
	uint32_t entropy_coding_mode_flag;
	uint32_t bottom_field_pic_order_in_frame_present_flag;
	uint32_t num_slice_groups;
	uint32_t slice_group_map_type;
	uint32_t run_length[8];
	uint32_t top_left[8];
	uint32_t bottom_right[8];
	uint32_t slice_group_change_direction_flag;
	uint32_t slice_group_change_rate;
	uint32_t pic_size_in_map_units;
	uint32_t *slice_group_id;
	uint32_t num_ref_idx_l0_default_active;
	uint32_t num_ref_idx_l1_default_active;
	uint32_t weighted_pred_flag;
	uint32_t weighted_bipred_idc;
	int32_t pic_init_qp_minus26;
	int32_t pic_init_qs_minus26;
	int32_t chroma_qp_index_offset;
	uint32_t deblocking_filter_control_present_flag;
	uint32_t constrained_intra_pred_flag;
	uint32_t redundant_pic_cnt_present_flag;
	/* start of new stuff */
	uint32_t transform_8x8_mode_flag;
	uint32_t chroma_format_idc;
	uint32_t pic_scaling_matrix_present_flag;
	uint32_t pic_scaling_list_present_flag[12];
	uint32_t use_default_scaling_matrix_flag[12];
	uint32_t pic_scaling_list_4x4[6][16];
	uint32_t pic_scaling_list_8x8[6][64];
	int32_t second_chroma_qp_index_offset;
	uint32_t ref_count[2];
};

struct h264_nal_svc_header {
	uint32_t idr_flag;
	uint32_t priority_id;
	uint32_t no_inter_layer_pred_flag;
	uint32_t dependency_id;
	uint32_t quality_id;
	uint32_t temporal_id;
	uint32_t use_ref_base_pic_flag;
	uint32_t discardable_flag;
	uint32_t output_flag;
};

struct h264_ref_pic_list_modification {
	uint32_t flag;
	struct h264_slice_ref_pic_list_modification_entry {
		uint32_t op;
		uint32_t param;
		uint32_t param2;
	} list[H264_MAX_REFS + 1];
};

struct h264_pred_weight_table_entry {
	uint32_t luma_weight_flag;
	int32_t luma_weight;
	int32_t luma_offset;
	uint32_t chroma_weight_flag;
	int32_t chroma_weight[2];
	int32_t chroma_offset[2];
};

struct h264_mmco {
	enum h264_mmco_opcode opcode;
	uint32_t short_pic_num; ///< pic_num without wrapping (pic_num & max_pic_num)
	uint32_t long_arg; ///< index, pic_num, or num long refs depending on opcode
};

struct h264_slice {
	uint32_t nal_ref_idc;
	uint32_t nal_unit_type;
	struct h264_nal_svc_header svc;
	uint32_t first_mb_in_slice;
	uint32_t header_size;
	uint32_t pic_parameter_set_id;

	uint32_t slice_type;
	uint32_t slice_type_fixed;
	uint32_t slice_type_nos;
	int picture_structure;

	uint32_t colour_plane_id;
	uint32_t frame_num;
	uint32_t field_pic_flag;
	uint32_t bottom_field_flag;
	uint32_t idr_pic_id;
	uint32_t pic_order_cnt_lsb;
	int32_t delta_pic_order_cnt_bottom;
	int32_t delta_pic_order_cnt[2];
	uint32_t redundant_pic_cnt;
	uint32_t direct_spatial_mb_pred_flag;
	uint32_t num_ref_idx_active_override_flag;
	uint32_t num_ref_idx_l0_active;
	uint32_t num_ref_idx_l1_active;
	struct h264_ref_pic_list_modification ref_pic_list_modification_l0;
	struct h264_ref_pic_list_modification ref_pic_list_modification_l1;

	uint32_t base_pred_weight_table_flag;
	uint32_t luma_log2_weight_denom;
	uint32_t chroma_log2_weight_denom;
	struct h264_pred_weight_table_entry pwt_l0[H264_MAX_REFS];
	struct h264_pred_weight_table_entry pwt_l1[H264_MAX_REFS];

	uint32_t no_output_of_prior_pics_flag;
	uint32_t long_term_reference_flag;
	uint32_t adaptive_ref_pic_marking_mode_flag;
	struct h264_mmco mmcos[H264_MAX_MMCO_COUNT];
	int num_mmcos;
	/* SVC base ref pic marking */
	uint32_t store_ref_base_pic_flag;
	uint32_t adaptive_ref_base_pic_marking_mode_flag;
	struct h264_mmco base_mmcos[H264_MAX_MMCO_COUNT];
	int num_base_mmcos;

	int32_t slice_qp_delta;
	uint32_t sp_for_switch_flag;
	int32_t slice_qs_delta;
	uint32_t cabac_init_idc;
	uint32_t disable_deblocking_filter_idc;
	int32_t slice_alpha_c0_offset_div2;
	int32_t slice_beta_offset_div2;
	uint32_t slice_group_change_cycle;

	/* derived stuff starts here */
	uint32_t width;
	uint32_t height;
	uint32_t width_mbs;
	uint32_t height_mbs;
	uint32_t pic_size_in_mbs;
	uint32_t mbaff_frame_flag;
	uint32_t last_mb_in_slice;
	uint32_t chroma_array_type;
	uint32_t bit_depth_luma_minus8;
	uint32_t bit_depth_chroma_minus8;
};

struct h264_context {
	struct bitstream gb;
	struct h264_sps sps_list[H264_MAX_SPS_COUNT];
	struct h264_pps pps_list[H264_MAX_PPS_COUNT];
	struct h264_sps sub_sps_list[H264_MAX_SPS_COUNT];
	struct h264_slice slice;
};

#define h264_get_pps(ctx, id) (&((ctx)->pps_list[(id)]))
#define h264_get_sps(ctx, id) \
	(&((ctx)->sps_list[(h264_get_pps(ctx, id)->seq_parameter_set_id)]))
#define h264_get_sub_sps(ctx, id) \
	(&((ctx)->sub_sps_list[(h264_get_pps(ctx, id)->seq_parameter_set_id)]))

int h264_find_nal_unit(uint8_t *buf, int size, int *nal_start, int *nal_end);
int h264_decode_nal_unit(struct h264_context *ctx, uint8_t *buf, int size);

void h264_print_sps(struct h264_sps *sps);
void h264_print_sps_ext(struct h264_sps *sps);
void h264_print_pps(struct h264_pps *pps);
void h264_print_slice_header(struct h264_context *ctx, struct h264_slice *slice);
void h264_print_slice_data(struct h264_slice *slice);

#endif /* __H264_H__ */
