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

#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <inttypes.h>

#include "bs.h"
#include "h2645.h"
#include "h265.h"
#include "h265_data.h"
#include "h265_print.h"
#include "util.h"

static void hevc_decode_sublayer_hdr(struct bitstream *gb, unsigned int nb_cpb,
                        struct hevc_sublayer_hdr_params *par, int subpic_params_present)
{
    unsigned int i;

    for (i = 0; i < nb_cpb; i++) {
        par->bit_rate_value_minus1[i] = get_ue_golomb_long(gb);
        par->cpb_size_value_minus1[i] = get_ue_golomb_long(gb);

        if (subpic_params_present) {
            par->cpb_size_du_value_minus1[i] = get_ue_golomb_long(gb);
            par->bit_rate_du_value_minus1[i] = get_ue_golomb_long(gb);
        }

        par->cbr_flag[i] = get_bits1(gb);
    }
}

static int hevc_decode_hdr(struct bitstream *gb, int common_inf_present,
                      struct hevc_hdr_params *hdr, int max_sublayers)
{
    int i;

    if (common_inf_present) {
        hdr->nal_hrd_parameters_present_flag = get_bits1(gb);
        hdr->vcl_hrd_parameters_present_flag = get_bits1(gb);

        if (hdr->nal_hrd_parameters_present_flag ||
            hdr->vcl_hrd_parameters_present_flag) {
            hdr->sub_pic_hrd_params_present_flag = get_bits1(gb);

            if (hdr->sub_pic_hrd_params_present_flag) {
                hdr->tick_divisor_minus2 = get_bits(gb, 8);
                hdr->du_cpb_removal_delay_increment_length_minus1 = get_bits(gb, 5);
                hdr->sub_pic_cpb_params_in_pic_timing_sei_flag = get_bits1(gb);
                hdr->dpb_output_delay_du_length_minus1 = get_bits(gb, 5);
            }

            hdr->bit_rate_scale = get_bits(gb, 4);
            hdr->cpb_size_scale = get_bits(gb, 4);

            if (hdr->sub_pic_hrd_params_present_flag)
                hdr->cpb_size_du_scale = get_bits(gb, 4);

            hdr->initial_cpb_removal_delay_length_minus1 = get_bits(gb, 5);
            hdr->au_cpb_removal_delay_length_minus1 = get_bits(gb, 5);
            hdr->dpb_output_delay_length_minus1 = get_bits(gb, 5);
        }
    }

    for (i = 0; i < max_sublayers; i++) {
        hdr->fixed_pic_rate_general_flag[i] = get_bits1(gb);

        if (!hdr->fixed_pic_rate_general_flag[i])
            hdr->fixed_pic_rate_within_cvs_flag[i] = get_bits1(gb);

        if (hdr->fixed_pic_rate_within_cvs_flag[i] ||
            hdr->fixed_pic_rate_general_flag[i])
            hdr->elemental_duration_in_tc_minus1[i] = get_ue_golomb_long(gb);
        else
            hdr->low_delay_hrd_flag[i] = get_bits1(gb);

        if (!hdr->low_delay_hrd_flag[i]) {
            hdr->cpb_cnt_minus1[i] = get_ue_golomb_long(gb);
            if (hdr->cpb_cnt_minus1[i] > 31) {
                h265_err("nb_cpb %d invalid\n", hdr->cpb_cnt_minus1[i]);
                return -EINVALDATA;
            }
        }

        if (hdr->nal_hrd_parameters_present_flag)
            hevc_decode_sublayer_hdr(gb, hdr->cpb_cnt_minus1[i]+1, &hdr->nal_params[i],
                                     hdr->sub_pic_hrd_params_present_flag);

        if (hdr->vcl_hrd_parameters_present_flag)
            hevc_decode_sublayer_hdr(gb, hdr->cpb_cnt_minus1[i]+1, &hdr->vcl_params[i],
                                     hdr->sub_pic_hrd_params_present_flag);
    }

    return 0;
}

static int hevc_common_profile_tier_level(struct bitstream *gb, struct hevc_ptl_common *ptl)
{
    int i;

    ptl->profile_space = get_bits(gb, 2);
    ptl->tier_flag     = get_bits1(gb);
    ptl->profile_idc   = get_bits(gb, 5);
    if (ptl->profile_idc == AV_PROFILE_HEVC_MAIN)
        h265_log("Main profile bitstream\n");
    else if (ptl->profile_idc == AV_PROFILE_HEVC_MAIN_10)
        h265_log("Main 10 profile bitstream\n");
    else if (ptl->profile_idc == AV_PROFILE_HEVC_MAIN_STILL_PICTURE)
        h265_log("Main Still Picture profile bitstream\n");
    else if (ptl->profile_idc == AV_PROFILE_HEVC_REXT)
        h265_log("Range Extension profile bitstream\n");
    else if (ptl->profile_idc == AV_PROFILE_HEVC_SCC)
        h265_log("Screen Content Coding Extension profile bitstream\n");
    else
        h265_wrn("Unknown HEVC profile: %d\n", ptl->profile_idc);

    for (i = 0; i < 32; i++) {
        ptl->profile_compatibility_flag[i] = get_bits1(gb);

        if (ptl->profile_idc == 0 && i > 0 && ptl->profile_compatibility_flag[i])
            ptl->profile_idc = i;
    }
    ptl->progressive_source_flag    = get_bits1(gb);
    ptl->interlaced_source_flag     = get_bits1(gb);
    ptl->non_packed_constraint_flag = get_bits1(gb);
    ptl->frame_only_constraint_flag = get_bits1(gb);

#define check_profile_idc(idc) \
        ptl->profile_idc == idc || ptl->profile_compatibility_flag[idc]

    if (check_profile_idc(4) || check_profile_idc(5) || check_profile_idc(6) ||
        check_profile_idc(7) || check_profile_idc(8) || check_profile_idc(9) ||
        check_profile_idc(10)) {

        ptl->max_12bit_constraint_flag        = get_bits1(gb);
        ptl->max_10bit_constraint_flag        = get_bits1(gb);
        ptl->max_8bit_constraint_flag         = get_bits1(gb);
        ptl->max_422chroma_constraint_flag    = get_bits1(gb);
        ptl->max_420chroma_constraint_flag    = get_bits1(gb);
        ptl->max_monochrome_constraint_flag   = get_bits1(gb);
        ptl->intra_constraint_flag            = get_bits1(gb);
        ptl->one_picture_only_constraint_flag = get_bits1(gb);
        ptl->lower_bit_rate_constraint_flag   = get_bits1(gb);

        if (check_profile_idc(5) || check_profile_idc(9) || check_profile_idc(10)) {
            ptl->max_14bit_constraint_flag    = get_bits1(gb);
            skip_bits_long(gb, 33); // XXX_reserved_zero_33bits[0..32]
        } else {
            skip_bits_long(gb, 34); // XXX_reserved_zero_34bits[0..33]
        }
    } else if (check_profile_idc(2)) {
        skip_bits(gb, 7);
        ptl->one_picture_only_constraint_flag = get_bits1(gb);
        skip_bits_long(gb, 35); // XXX_reserved_zero_35bits[0..34]
    } else {
        skip_bits_long(gb, 43); // XXX_reserved_zero_43bits[0..42]
    }

    if (check_profile_idc(1) || check_profile_idc(2) || check_profile_idc(3) ||
        check_profile_idc(4) || check_profile_idc(5) || check_profile_idc(9))
        ptl->inbld_flag = get_bits1(gb);
    else
        skip_bits1(gb);
#undef check_profile_idc

    return 0;
}

static int hevc_profile_tier_level(struct bitstream *gb,
                                   struct hevc_ptl *ptl, int max_num_sub_layers)
{
    int i;

    if (hevc_common_profile_tier_level(gb, &ptl->general_ptl) < 0) {
        h265_err("PTL information too short\n");
        return -EINVALDATA;
    }

    ptl->general_ptl.level_idc = get_bits(gb, 8);

    for (i = 0; i < max_num_sub_layers - 1; i++) {
        ptl->sub_layer_profile_present_flag[i] = get_bits1(gb);
        ptl->sub_layer_level_present_flag[i]   = get_bits1(gb);
    }

    if (max_num_sub_layers - 1 > 0)
        for (i = max_num_sub_layers - 1; i < 8; i++)
            skip_bits(gb, 2); // reserved_zero_2bits[i]
    for (i = 0; i < max_num_sub_layers - 1; i++) {
        if (ptl->sub_layer_profile_present_flag[i] &&
            hevc_common_profile_tier_level(gb, &ptl->sub_layer_ptl[i]) < 0) {
            h265_err("PTL information for sublayer %i too short\n", i);
            return -EINVALDATA;
        }
        if (ptl->sub_layer_level_present_flag[i])
            ptl->sub_layer_ptl[i].level_idc = get_bits(gb, 8);
    }

    return 0;
}

static int hevc_decode_nal_vps(struct h265_context *s, struct hevc_vps *vps)
{
	struct bitstream *gb = &s->gb;
	int vps_id;
	int i, j;

	vps_id = vps->vps_id = get_bits(gb, 4);

	vps->vps_base_layer_internal_flag = get_bits1(gb);
	vps->vps_base_layer_available_flag = get_bits1(gb);
	vps->vps_max_layers = get_bits(gb, 6) + 1;
	vps->vps_max_sub_layers = get_bits(gb, 3) + 1;
	vps->vps_temporal_id_nesting_flag = get_bits1(gb);

	if (get_bits(gb, 16) != 0xffff) { // vps_reserved_ffff_16bits
		h265_err("vps_reserved_ffff_16bits is not 0xffff\n");
		goto err;
	}

	if (vps->vps_max_sub_layers > HEVC_MAX_SUB_LAYERS) {
		h265_err("vps_max_sub_layers out of range: %d\n",
		       vps->vps_max_sub_layers);
		goto err;
	}

	if (hevc_profile_tier_level(gb, &vps->ptl, vps->vps_max_sub_layers) < 0)
		goto err;

	vps->vps_sub_layer_ordering_info_present_flag = get_bits1(gb);

	i = vps->vps_sub_layer_ordering_info_present_flag ? 0 :
							    vps->vps_max_sub_layers - 1;
	for (; i < vps->vps_max_sub_layers; i++) {
		vps->vps_max_dec_pic_buffering[i] = get_ue_golomb_long(gb) + 1;
		vps->vps_max_num_reorder_pics[i] = get_ue_golomb_long(gb);
		vps->vps_max_latency_increase[i] = get_ue_golomb_long(gb) - 1;

		if (vps->vps_max_dec_pic_buffering[i] > HEVC_MAX_DPB_SIZE ||
		    !vps->vps_max_dec_pic_buffering[i]) {
			h265_err("vps_max_dec_pic_buffering_minus1 out of range: %d\n",
			       vps->vps_max_dec_pic_buffering[i] - 1);
			goto err;
		}
		if (vps->vps_max_num_reorder_pics[i] >
		    vps->vps_max_dec_pic_buffering[i] - 1) {
			h265_err("vps_max_num_reorder_pics out of range: %d\n",
			       vps->vps_max_num_reorder_pics[i]);
            goto err;
		}
	}

	vps->vps_max_layer_id = get_bits(gb, 6);
	vps->vps_num_layer_sets = get_ue_golomb_long(gb) + 1;
	if (vps->vps_num_layer_sets < 1 || vps->vps_num_layer_sets > 1024) {
		h265_err("too many layer_id_included_flags\n");
		goto err;
	}

	for (i = 1; i < vps->vps_num_layer_sets; i++)
		for (j = 0; j <= vps->vps_max_layer_id; j++)
			skip_bits(gb, 1); // layer_id_included_flag[i][j]

	vps->vps_timing_info_present_flag = get_bits1(gb);
	if (vps->vps_timing_info_present_flag) {
		vps->vps_num_units_in_tick = get_bits_long(gb, 32);
		vps->vps_time_scale = get_bits_long(gb, 32);
		vps->vps_poc_proportional_to_timing_flag = get_bits1(gb);
		if (vps->vps_poc_proportional_to_timing_flag)
			vps->vps_num_ticks_poc_diff_one = get_ue_golomb_long(gb) + 1;
		vps->vps_num_hrd_parameters = get_ue_golomb_long(gb);
		if (vps->vps_num_hrd_parameters > vps->vps_num_layer_sets) {
			h265_err("vps_num_hrd_parameters %d is invalid\n",
			       vps->vps_num_hrd_parameters);
			goto err;
		}
		for (i = 0; i < vps->vps_num_hrd_parameters; i++) {
			vps->hrd_layer_set_idx[i] = get_ue_golomb_long(gb);
			if (i)
				vps->cprms_present_flag[i] = get_bits1(gb);
            else
                vps->cprms_present_flag[i] = 1;
			hevc_decode_hdr(gb, vps->cprms_present_flag[i], &vps->hdr[i],
				   vps->vps_max_sub_layers);
		}
	}

	if (get_bits1(gb)) /* vps_extension_flag */
		h2645_more_rbsp_data(gb);

	s->vps_list[vps_id] = *vps;
	h2645_rbsp_trailing_bits(gb);

err:
	return 0;
}

static int hevc_decode_st_rps(struct bitstream *gb, struct hevc_short_term_rps *rps,
                              const struct hevc_sps *sps, int is_slice_header)
{
    int delta_poc;
    int k0 = 0;
    int k  = 0;
    int i;

    rps->inter_ref_pic_set_prediction_flag = 0;

    if (rps != sps->st_rps && sps->nb_st_rps)
        rps->inter_ref_pic_set_prediction_flag = get_bits1(gb);

    if (rps->inter_ref_pic_set_prediction_flag) {
        const struct hevc_short_term_rps *rps_ridx;
        int delta_rps;

        if (is_slice_header) {
            rps->delta_idx = get_ue_golomb_long(gb) + 1;
            if (rps->delta_idx > sps->nb_st_rps) {
                h265_err("Invalid value of delta_idx in slice header RPS: %d > %d.\n",
                       rps->delta_idx, sps->nb_st_rps);
                return -EINVALDATA;
            }
            rps_ridx = &sps->st_rps[sps->nb_st_rps - rps->delta_idx];
            rps->rps_idx_num_delta_pocs = rps_ridx->num_delta_pocs;
        } else
            rps_ridx = &sps->st_rps[rps - sps->st_rps - 1];

        rps->delta_rps_sign = get_bits1(gb);
        rps->abs_delta_rps  = get_ue_golomb_long(gb) + 1;
        if (rps->abs_delta_rps > 32768) {
            h265_err("Invalid value of abs_delta_rps: %d\n", rps->abs_delta_rps);
            return -EINVALDATA;
        }
        delta_rps      = (1 - (rps->delta_rps_sign << 1)) * rps->abs_delta_rps;
        for (i = 0; i <= rps_ridx->num_delta_pocs; i++) {
            int used = rps->used[k] = get_bits1(gb);

            rps->use_delta_flag = 0;
            if (!used)
                rps->use_delta_flag = get_bits1(gb);

            if (used || rps->use_delta_flag) {
                if (i < rps_ridx->num_delta_pocs)
                    delta_poc = delta_rps + rps_ridx->delta_poc[i];
                else
                    delta_poc = delta_rps;
                rps->delta_poc[k] = delta_poc;
                if (delta_poc < 0)
                    k0++;
                k++;
            }
        }

        if (k >= ARRAY_SIZE(rps->used)) {
            h265_err("Invalid num_delta_pocs: %d\n", k);
            return -EINVALDATA;
        }

        rps->num_delta_pocs    = k;
        rps->num_negative_pics = k0;
        // sort in increasing order (smallest first)
        if (rps->num_delta_pocs != 0) {
            int used, tmp;
            for (i = 1; i < rps->num_delta_pocs; i++) {
                delta_poc = rps->delta_poc[i];
                used      = rps->used[i];
                for (k = i - 1; k >= 0; k--) {
                    tmp = rps->delta_poc[k];
                    if (delta_poc < tmp) {
                        rps->delta_poc[k + 1] = tmp;
                        rps->used[k + 1]      = rps->used[k];
                        rps->delta_poc[k]     = delta_poc;
                        rps->used[k]          = used;
                    }
                }
            }
        }
        if ((rps->num_negative_pics >> 1) != 0) {
            int used;
            k = rps->num_negative_pics - 1;
            // flip the negative values to largest first
            for (i = 0; i < rps->num_negative_pics >> 1; i++) {
                delta_poc         = rps->delta_poc[i];
                used              = rps->used[i];
                rps->delta_poc[i] = rps->delta_poc[k];
                rps->used[i]      = rps->used[k];
                rps->delta_poc[k] = delta_poc;
                rps->used[k]      = used;
                k--;
            }
        }
    } else {
        unsigned int prev;
        rps->num_negative_pics = get_ue_golomb_long(gb);
        rps->num_positive_pics = get_ue_golomb_long(gb);

        if (rps->num_negative_pics >= HEVC_MAX_REFS ||
            rps->num_positive_pics >= HEVC_MAX_REFS) {
            h265_err("Too many refs in a short term RPS.\n");
            return -EINVALDATA;
        }

        rps->num_delta_pocs = rps->num_negative_pics + rps->num_positive_pics;
        if (rps->num_delta_pocs) {
            prev = 0;
            for (i = 0; i < rps->num_negative_pics; i++) {
                delta_poc = rps->delta_poc_s0[i] = get_ue_golomb_long(gb) + 1;
                if (delta_poc < 1 || delta_poc > 32768) {
                    h265_err("Invalid value of delta_poc: %d\n", delta_poc);
                    return -EINVALDATA;
                }
                prev -= delta_poc;
                rps->delta_poc[i] = prev;
                rps->used[i]      = get_bits1(gb);
            }
            prev = 0;
            for (i = 0; i < rps->num_positive_pics; i++) {
                delta_poc = rps->delta_poc_s1[i] = get_ue_golomb_long(gb) + 1;
                if (delta_poc < 1 || delta_poc > 32768) {
                    h265_err("Invalid value of delta_poc: %d\n", delta_poc);
                    return -EINVALDATA;
                }
                prev += delta_poc;
                rps->delta_poc[rps->num_negative_pics + i] = prev;
                rps->used[rps->num_negative_pics + i]      = get_bits1(gb);
            }
        }
    }

    return 0;
}

static int hevc_decode_lt_rps(struct bitstream *gb, struct hevc_long_term_rps *rps,
                              const struct hevc_sps *sps, struct h265_context *s)
{
    int max_poc_lsb      = 1 << sps->log2_max_poc_lsb;
    int prev_delta_msb   = 0;
    unsigned int nb_sps  = 0, nb_sh;
    int i;

    rps->nb_refs = 0;
    if (!sps->long_term_ref_pics_present_flag)
        return 0;

    if (sps->num_long_term_ref_pics_sps > 0)
        nb_sps = get_ue_golomb_long(gb);
    nb_sh = get_ue_golomb_long(gb);

    if (nb_sps > sps->num_long_term_ref_pics_sps)
        return -EINVALDATA;
    if (nb_sh + (uint64_t)nb_sps > ARRAY_SIZE(rps->poc))
        return -EINVALDATA;

    rps->nb_refs = nb_sh + nb_sps;

    for (i = 0; i < rps->nb_refs; i++) {

        if (i < nb_sps) {
            uint8_t lt_idx_sps = 0;

            if (sps->num_long_term_ref_pics_sps > 1)
                lt_idx_sps = get_bits(gb, clog2(sps->num_long_term_ref_pics_sps));

            rps->poc[i]  = sps->lt_ref_pic_poc_lsb_sps[lt_idx_sps];
            rps->used[i] = sps->used_by_curr_pic_lt_sps_flag[lt_idx_sps];
        } else {
            rps->poc[i]  = get_bits(gb, sps->log2_max_poc_lsb);
            rps->used[i] = get_bits1(gb);
        }

        rps->poc_msb_present[i] = get_bits1(gb);
        if (rps->poc_msb_present[i]) {
            int64_t delta = get_ue_golomb_long(gb);
            int64_t poc;

            if (i && i != nb_sps)
                delta += prev_delta_msb;

            poc = rps->poc[i] + s->poc - delta * max_poc_lsb - s->sh.pic_order_cnt_lsb;
            if (poc != (int32_t)poc)
                return -EINVALDATA;
            rps->poc[i] = poc;
            prev_delta_msb = delta;
        }
    }

    return 0;
}

static void set_default_scaling_list_data(ScalingList *sl)
{
    int matrixId;

    for (matrixId = 0; matrixId < 6; matrixId++) {
        // 4x4 default is 16
        memset(sl->sl[0][matrixId], 16, 16);
        sl->sl_dc[0][matrixId] = 16; // default for 16x16
        sl->sl_dc[1][matrixId] = 16; // default for 32x32
    }
    memcpy(sl->sl[1][0], default_scaling_list_intra, 64);
    memcpy(sl->sl[1][1], default_scaling_list_intra, 64);
    memcpy(sl->sl[1][2], default_scaling_list_intra, 64);
    memcpy(sl->sl[1][3], default_scaling_list_inter, 64);
    memcpy(sl->sl[1][4], default_scaling_list_inter, 64);
    memcpy(sl->sl[1][5], default_scaling_list_inter, 64);
    memcpy(sl->sl[2][0], default_scaling_list_intra, 64);
    memcpy(sl->sl[2][1], default_scaling_list_intra, 64);
    memcpy(sl->sl[2][2], default_scaling_list_intra, 64);
    memcpy(sl->sl[2][3], default_scaling_list_inter, 64);
    memcpy(sl->sl[2][4], default_scaling_list_inter, 64);
    memcpy(sl->sl[2][5], default_scaling_list_inter, 64);
    memcpy(sl->sl[3][0], default_scaling_list_intra, 64);
    memcpy(sl->sl[3][1], default_scaling_list_intra, 64);
    memcpy(sl->sl[3][2], default_scaling_list_intra, 64);
    memcpy(sl->sl[3][3], default_scaling_list_inter, 64);
    memcpy(sl->sl[3][4], default_scaling_list_inter, 64);
    memcpy(sl->sl[3][5], default_scaling_list_inter, 64);
}

static int hevc_decode_scaling_list(struct bitstream *gb,
                                    ScalingList *sl, const struct hevc_sps *sps)
{
    uint8_t scaling_list_pred_mode_flag;
    uint8_t scaling_list_dc_coef[2][6];
    int size_id, matrix_id, pos;
    int i;

    for (size_id = 0; size_id < 4; size_id++) {
        for (matrix_id = 0; matrix_id < 6; matrix_id += ((size_id == 3) ? 3 : 1)) {
            scaling_list_pred_mode_flag = get_bits1(gb);
            if (!scaling_list_pred_mode_flag) {
                unsigned int delta = get_ue_golomb_long(gb);
                /* Only need to handle non-zero delta. Zero means default,
                 * which should already be in the arrays. */
                if (delta) {
                    // Copy from previous array.
                    delta *= (size_id == 3) ? 3 : 1;
                    if (matrix_id < delta) {
                        h265_err("Invalid delta in scaling list data: %d.\n", delta);
                        return -EINVALDATA;
                    }

                    memcpy(sl->sl[size_id][matrix_id],
                           sl->sl[size_id][matrix_id - delta],
                           size_id > 0 ? 64 : 16);
                    if (size_id > 1)
                        sl->sl_dc[size_id - 2][matrix_id] = sl->sl_dc[size_id - 2][matrix_id - delta];
                }
            } else {
                int next_coef, coef_num;
                int32_t scaling_list_delta_coef;

                next_coef = 8;
                coef_num  = FFMIN(64, 1 << (4 + (size_id << 1)));
                if (size_id > 1) {
                    int scaling_list_coeff_minus8 = get_se_golomb(gb);
                    if (scaling_list_coeff_minus8 < -7 ||
                        scaling_list_coeff_minus8 > 247)
                        return -EINVALDATA;
                    scaling_list_dc_coef[size_id - 2][matrix_id] = scaling_list_coeff_minus8 + 8;
                    next_coef = scaling_list_dc_coef[size_id - 2][matrix_id];
                    sl->sl_dc[size_id - 2][matrix_id] = next_coef;
                }
                for (i = 0; i < coef_num; i++) {
                    if (size_id == 0)
                        pos = 4 * ff_hevc_diag_scan4x4_y[i] +
                                  ff_hevc_diag_scan4x4_x[i];
                    else
                        pos = 8 * ff_hevc_diag_scan8x8_y[i] +
                                  ff_hevc_diag_scan8x8_x[i];

                    scaling_list_delta_coef = get_se_golomb(gb);
                    next_coef = (next_coef + 256U + scaling_list_delta_coef) % 256;
                    sl->sl[size_id][matrix_id][pos] = next_coef;
                }
            }
        }
    }

    if (sps->chroma_format_idc == 3) {
        for (i = 0; i < 64; i++) {
            sl->sl[3][1][i] = sl->sl[2][1][i];
            sl->sl[3][2][i] = sl->sl[2][2][i];
            sl->sl[3][4][i] = sl->sl[2][4][i];
            sl->sl[3][5][i] = sl->sl[2][5][i];
        }
        sl->sl_dc[1][1] = sl->sl_dc[0][1];
        sl->sl_dc[1][2] = sl->sl_dc[0][2];
        sl->sl_dc[1][4] = sl->sl_dc[0][4];
        sl->sl_dc[1][5] = sl->sl_dc[0][5];
    }

    return 0;
}

static void hevc_decode_vui(struct bitstream *gb, struct hevc_sps *sps)
{
    struct hevc_vui *vui = &sps->vui;

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
				h265_wrn("WARNING: unknown aspect_ratio_idc %d\n",
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

    vui->neutral_chroma_indication_flag = get_bits1(gb);
    vui->field_seq_flag                 = get_bits1(gb);
    vui->frame_field_info_present_flag  = get_bits1(gb);

    vui->default_display_window_flag = get_bits1(gb);
    if (vui->default_display_window_flag) {
        int vert_mult  = hevc_sub_height_c[sps->chroma_format_idc];
        int horiz_mult = hevc_sub_width_c[sps->chroma_format_idc];
        vui->def_disp_win_left_offset   = get_ue_golomb_long(gb) * horiz_mult;
        vui->def_disp_win_right_offset  = get_ue_golomb_long(gb) * horiz_mult;
        vui->def_disp_win_top_offset    = get_ue_golomb_long(gb) *  vert_mult;
        vui->def_disp_win_bottom_offset = get_ue_golomb_long(gb) *  vert_mult;

        if (1) {
            h265_wrn("discarding vui default display window, "
                     "original values are l:%u r:%u t:%u b:%u\n",
                   vui->def_disp_win_left_offset,
                   vui->def_disp_win_right_offset,
                   vui->def_disp_win_top_offset,
                   vui->def_disp_win_bottom_offset);

            vui->def_disp_win_left_offset   =
            vui->def_disp_win_right_offset  =
            vui->def_disp_win_top_offset    =
            vui->def_disp_win_bottom_offset = 0;
        }
    }

    vui->vui_timing_info_present_flag = get_bits1(gb);
    if (vui->vui_timing_info_present_flag) {
        vui->vui_num_units_in_tick               = get_bits_long(gb, 32);
        vui->vui_time_scale                      = get_bits_long(gb, 32);
        vui->vui_poc_proportional_to_timing_flag = get_bits1(gb);
        if (vui->vui_poc_proportional_to_timing_flag)
            vui->vui_num_ticks_poc_diff_one_minus1 = get_ue_golomb_long(gb);
        vui->vui_hrd_parameters_present_flag = get_bits1(gb);
        if (vui->vui_hrd_parameters_present_flag)
            hevc_decode_hdr(gb, 1, &sps->hdr, sps->max_sub_layers);
    }

    vui->bitstream_restriction_flag = get_bits1(gb);
    if (vui->bitstream_restriction_flag) {
        vui->tiles_fixed_structure_flag              = get_bits1(gb);
        vui->motion_vectors_over_pic_boundaries_flag = get_bits1(gb);
        vui->restricted_ref_pic_lists_flag           = get_bits1(gb);
        vui->min_spatial_segmentation_idc            = get_ue_golomb_long(gb);
        vui->max_bytes_per_pic_denom                 = get_ue_golomb_long(gb);
        vui->max_bits_per_min_cu_denom               = get_ue_golomb_long(gb);
        vui->log2_max_mv_length_horizontal           = get_ue_golomb_long(gb);
        vui->log2_max_mv_length_vertical             = get_ue_golomb_long(gb);
    }
    else {
        vui->tiles_fixed_structure_flag              = 0;
        vui->motion_vectors_over_pic_boundaries_flag = 1;
        vui->min_spatial_segmentation_idc            = 0;
        vui->max_bytes_per_pic_denom                 = 2;
        vui->max_bits_per_min_cu_denom               = 1;
        vui->log2_max_mv_length_horizontal           = 15;
        vui->log2_max_mv_length_vertical             = 15;
    }
}

static int h265_decode_nal_sps(struct h265_context *s, struct hevc_sps *sps)
{
    int bit_depth_chroma, start, num_comps;
    struct bitstream *gb = &s->gb;
    int ret, sps_id, i;

    sps->sps_video_parameter_set_id = get_bits(gb, 4);
#if 0
    if (vps_list && !vps_list[sps->vps_id]) {
        h265_err("VPS %d does not exist\n", sps->vps_id);
        return -1;
    }
#endif

    sps->max_sub_layers = get_bits(gb, 3) + 1;
    if (sps->max_sub_layers > HEVC_MAX_SUB_LAYERS) {
        h265_err("sps_max_sub_layers out of range: %d\n", sps->max_sub_layers);
        return -EINVALDATA;
    }

    sps->sps_temporal_id_nesting_flag = get_bits(gb, 1);

    if ((ret = hevc_profile_tier_level(gb, &sps->ptl, sps->max_sub_layers)) < 0)
        return ret;

    sps_id = sps->sps_seq_parameter_set_id = get_ue_golomb_long(gb);
    if (sps_id >= HEVC_MAX_SPS_COUNT) {
        h265_err("SPS id out of range: %d\n", sps_id);
        return -EINVALDATA;
    }

    sps->chroma_format_idc = get_ue_golomb_long(gb);
    if (sps->chroma_format_idc > 3U) {
        h265_err("chroma_format_idc %d is invalid\n", sps->chroma_format_idc);
        return -EINVALDATA;
    }

    if (sps->chroma_format_idc == 3)
        sps->separate_colour_plane_flag = get_bits1(gb);

    if (sps->separate_colour_plane_flag)
        sps->chroma_format_idc = 0;

    sps->pic_width_in_luma_samples  = get_ue_golomb_long(gb);
    sps->pic_height_in_luma_samples = get_ue_golomb_long(gb);

    sps->conformance_window_flag = get_bits1(gb);
    if (sps->conformance_window_flag) {
        int vert_mult  = hevc_sub_height_c[sps->chroma_format_idc];
        int horiz_mult = hevc_sub_width_c[sps->chroma_format_idc];
        sps->conf_win_left_offset   = get_ue_golomb_long(gb) * horiz_mult;
        sps->conf_win_right_offset  = get_ue_golomb_long(gb) * horiz_mult;
        sps->conf_win_top_offset    = get_ue_golomb_long(gb) *  vert_mult;
        sps->conf_win_bottom_offset = get_ue_golomb_long(gb) *  vert_mult;
    }
    else {
        sps->conf_win_left_offset   = 0;
        sps->conf_win_right_offset  = 0;
        sps->conf_win_top_offset    = 0;
        sps->conf_win_bottom_offset = 0;
    }

    sps->bit_depth = get_ue_golomb_31(gb) + 8;
    if (sps->bit_depth > 16) {
        h265_err("Luma bit depth (%d) is out of range\n", sps->bit_depth);
        return -EINVALDATA;
    }
    bit_depth_chroma = get_ue_golomb_31(gb) + 8;
    if (bit_depth_chroma > 16) {
        h265_err("Chroma bit depth (%d) is out of range\n", bit_depth_chroma);
        return -EINVALDATA;
    }
    if (sps->chroma_format_idc && bit_depth_chroma != sps->bit_depth) {
        h265_err("Luma bit depth (%d) is different from chroma bit depth (%d), "
               "this is unsupported.\n",
               sps->bit_depth, bit_depth_chroma);
        return -EINVALDATA;
    }
    sps->bit_depth_chroma = bit_depth_chroma;

    sps->log2_max_poc_lsb = get_ue_golomb_long(gb) + 4;
    if (sps->log2_max_poc_lsb > 16) {
        h265_err("log2_max_pic_order_cnt_lsb_minus4 out range: %d\n",
               sps->log2_max_poc_lsb - 4);
        return -EINVALDATA;
    }

    sps->sps_sub_layer_ordering_info_present_flag = get_bits1(gb);
    start = sps->sps_sub_layer_ordering_info_present_flag ? 0 : sps->max_sub_layers - 1;
    for (i = start; i < sps->max_sub_layers; i++) {
        sps->sps_max_dec_pic_buffering[i] = get_ue_golomb_long(gb) + 1;
        sps->sps_max_num_reorder_pics[i]  = get_ue_golomb_long(gb);
        sps->sps_max_latency_increase[i]  = get_ue_golomb_long(gb) - 1;
        if (sps->sps_max_dec_pic_buffering[i] > (unsigned)HEVC_MAX_DPB_SIZE) {
            h265_err("sps_max_dec_pic_buffering_minus1 out of range: %d\n",
                   sps->sps_max_dec_pic_buffering[i] - 1U);
            return -EINVALDATA;
        }
        if (sps->sps_max_num_reorder_pics[i] > sps->sps_max_dec_pic_buffering[i] - 1) {
            h265_err("sps_max_num_reorder_pics out of range: %d\n",
                   sps->sps_max_num_reorder_pics[i]);
            if (sps->sps_max_num_reorder_pics[i] > HEVC_MAX_DPB_SIZE - 1) {
                return -EINVALDATA;
            }
            sps->sps_max_dec_pic_buffering[i] = sps->sps_max_num_reorder_pics[i] + 1;
        }
    }

    if (!sps->sps_sub_layer_ordering_info_present_flag) {
        for (i = 0; i < start; i++) {
            sps->sps_max_dec_pic_buffering[i] = sps->sps_max_dec_pic_buffering[start];
            sps->sps_max_num_reorder_pics[i]  = sps->sps_max_num_reorder_pics[start];
            sps->sps_max_latency_increase[i]  = sps->sps_max_latency_increase[start];
        }
    }

    sps->log2_min_cb_size                       = get_ue_golomb_long(gb) + 3;
    sps->log2_diff_max_min_coding_block_size    = get_ue_golomb_long(gb);
    sps->log2_min_tb_size                       = get_ue_golomb_long(gb) + 2;
    sps->log2_diff_max_min_transform_block_size = get_ue_golomb_long(gb);

    if (sps->log2_min_cb_size < 3 || sps->log2_min_cb_size > 30) {
        h265_err("Invalid value %d for log2_min_cb_size", sps->log2_min_cb_size);
        return -EINVALDATA;
    }

    if (sps->log2_diff_max_min_coding_block_size > 30) {
        h265_err("Invalid value %d for log2_diff_max_min_coding_block_size", sps->log2_diff_max_min_coding_block_size);
        return -EINVALDATA;
    }

    if (sps->log2_min_tb_size >= sps->log2_min_cb_size || sps->log2_min_tb_size < 2) {
        h265_err("Invalid value for log2_min_tb_size");
        return -EINVALDATA;
    }

    if (sps->log2_diff_max_min_transform_block_size > 30) {
        h265_err("Invalid value %d for log2_diff_max_min_transform_block_size",
               sps->log2_diff_max_min_transform_block_size);
        return -EINVALDATA;
    }

    sps->max_transform_hierarchy_depth_inter = get_ue_golomb_long(gb);
    sps->max_transform_hierarchy_depth_intra = get_ue_golomb_long(gb);

    sps->scaling_list_enable_flag = get_bits1(gb);
    if (sps->scaling_list_enable_flag) {
        set_default_scaling_list_data(&sps->scaling_list);

        sps->sps_scaling_list_data_present_flag = get_bits1(gb);
        if (sps->sps_scaling_list_data_present_flag) {
            ret = hevc_decode_scaling_list(gb, &sps->scaling_list, sps);
            if (ret < 0)
                return ret;
        }
    }

    sps->amp_enabled_flag                    = get_bits1(gb);
    sps->sample_adaptive_offset_enabled_flag = get_bits1(gb);

    sps->pcm_enabled_flag = get_bits1(gb);
    if (sps->pcm_enabled_flag) {
        sps->pcm_sample_bit_depth_luma   = get_bits(gb, 4) + 1;
        sps->pcm_sample_bit_depth_chroma = get_bits(gb, 4) + 1;
        sps->log2_min_pcm_cb_size = get_ue_golomb_long(gb) + 3;
        sps->log2_max_pcm_cb_size = sps->log2_min_pcm_cb_size + get_ue_golomb_long(gb);
        if (FFMAX(sps->pcm_sample_bit_depth_luma, sps->pcm_sample_bit_depth_chroma)
                    > sps->bit_depth) {
            h265_err("PCM bit depth (%d, %d) is greater than normal bit depth (%d)\n",
                   sps->pcm_sample_bit_depth_luma, sps->pcm_sample_bit_depth_chroma,
                   sps->bit_depth);
            return -EINVALDATA;
        }
        sps->pcm_loop_filter_disabled_flag = get_bits1(gb);
    }

    sps->num_short_term_ref_pic_sets = get_ue_golomb_long(gb);
    if (sps->num_short_term_ref_pic_sets > HEVC_MAX_SHORT_TERM_REF_PIC_SETS) {
        h265_err("Too many short term RPS: %d\n", sps->num_short_term_ref_pic_sets);
        return -EINVALDATA;
    }
    for (i = 0; i < sps->num_short_term_ref_pic_sets; i++) {
        if ((ret = hevc_decode_st_rps(gb, &sps->st_rps[i], sps, 0)) < 0)
            return ret;
    }

    sps->long_term_ref_pics_present_flag = get_bits1(gb);
    if (sps->long_term_ref_pics_present_flag) {
        sps->num_long_term_ref_pics_sps = get_ue_golomb_long(gb);
        if (sps->num_long_term_ref_pics_sps > HEVC_MAX_LONG_TERM_REF_PICS) {
            h265_err("Too many long term ref pics: %d.\n",
                   sps->num_long_term_ref_pics_sps);
            return -EINVALDATA;
        }
        for (i = 0; i < sps->num_long_term_ref_pics_sps; i++) {
            sps->lt_ref_pic_poc_lsb_sps[i]       = get_bits(gb, sps->log2_max_poc_lsb);
            sps->used_by_curr_pic_lt_sps_flag[i] = get_bits1(gb);
        }
    }

    sps->sps_temporal_mvp_enabled_flag          = get_bits1(gb);
    sps->sps_strong_intra_smoothing_enable_flag = get_bits1(gb);

    sps->vui_parameters_present_flag = get_bits1(gb);
    if (sps->vui_parameters_present_flag)
        hevc_decode_vui(gb, sps);

    sps->sps_extension_present_flag = get_bits1(gb);
    if (sps->sps_extension_present_flag) {
        sps->sps_range_extension_flag      = get_bits1(gb);
        sps->sps_multilayer_extension_flag = get_bits1(gb);
        sps->sps_3d_extension_flag         = get_bits1(gb);
        sps->sps_scc_extension_flag        = get_bits1(gb);
        sps->sps_extension_4bits           = get_bits(gb, 4);

        if (sps->sps_range_extension_flag) {
            sps->transform_skip_rotation_enabled_flag = get_bits1(gb);
            sps->transform_skip_context_enabled_flag  = get_bits1(gb);
            sps->implicit_rdpcm_enabled_flag = get_bits1(gb);
            sps->explicit_rdpcm_enabled_flag = get_bits1(gb);

            sps->extended_precision_processing_flag = get_bits1(gb);
            if (sps->extended_precision_processing_flag)
                h265_err("extended_precision_processing_flag not yet implemented\n");

            sps->intra_smoothing_disabled_flag       = get_bits1(gb);
            sps->high_precision_offsets_enabled_flag = get_bits1(gb);
            if (sps->high_precision_offsets_enabled_flag)
                h265_err("high_precision_offsets_enabled_flag not yet implemented\n");

            sps->persistent_rice_adaptation_enabled_flag = get_bits1(gb);
            sps->cabac_bypass_alignment_enabled_flag     = get_bits1(gb);
            if (sps->cabac_bypass_alignment_enabled_flag)
                h265_err("cabac_bypass_alignment_enabled_flag not yet implemented\n");
        }

        if (sps->sps_multilayer_extension_flag) {
            sps->inter_view_mv_vert_constraint_flag = get_bits1(gb);
            h265_err("sps_multilayer_extension_flag not yet implemented\n");
        }

        if (sps->sps_3d_extension_flag) {
            for (i = 0; i < 2; i++) {
                sps->iv_di_mc_enabled_flag[i] = get_bits1(gb);
                sps->iv_mv_scal_enabled_flag[i] = get_bits1(gb);
                if (i == 0) {
                    sps->log2_ivmc_sub_pb_size_minus3[i] = get_ue_golomb_long(gb);
                    sps->iv_res_pred_enabled_flag = get_bits1(gb);
                    sps->depth_ref_enabled_flag = get_bits1(gb);
                    sps->vsp_mc_enabled_flag = get_bits1(gb);
                    sps->dbbp_enabled_flag = get_bits1(gb);
                } else {
                    sps->tex_mc_enabled_flag = get_bits1(gb);
                    sps->log2_ivmc_sub_pb_size_minus3[i] = get_ue_golomb_long(gb);
                    sps->intra_contour_enabled_flag = get_bits1(gb);
                    sps->intra_dc_only_wedge_enabled_flag = get_bits1(gb);
                    sps->cqt_cu_part_pred_enabled_flag = get_bits1(gb);
                    sps->inter_dc_only_enabled_flag = get_bits1(gb);
                    sps->skip_intra_enabled_flag = get_bits1(gb);
                }
            }
            h265_err("sps_3d_extension_flag not yet implemented\n");
        }

        if (sps->sps_scc_extension_flag) {
            sps->sps_curr_pic_ref_enabled_flag = get_bits1(gb);
            sps->palette_mode_enabled_flag     = get_bits1(gb);
            if (sps->palette_mode_enabled_flag) {
                sps->palette_max_size = get_ue_golomb(gb);
                sps->delta_palette_max_predictor_size = get_ue_golomb(gb);
                sps->sps_palette_predictor_initializer_present_flag = get_bits1(gb);

                if (sps->sps_palette_predictor_initializer_present_flag) {
                    sps->sps_num_palette_predictor_initializer = get_ue_golomb(gb) + 1;
                    if (sps->sps_num_palette_predictor_initializer > HEVC_MAX_PALETTE_PREDICTOR_SIZE) {
                        h265_err("sps_num_palette_predictor_initializer out of range: %u\n",
                               sps->sps_num_palette_predictor_initializer);
                        return -EINVALDATA;
                    }
                    num_comps = !sps->chroma_format_idc ? 1 : 3;
                    for (int comp = 0; comp < num_comps; comp++) {
                        int bit_depth = !comp ? sps->bit_depth : sps->bit_depth_chroma;
                        for (i = 0; i < sps->sps_num_palette_predictor_initializer; i++)
                            sps->sps_palette_predictor_initializer[comp][i] = get_bits(gb, bit_depth);
                    }
                }
            }
            sps->motion_vector_resolution_control_idc   = get_bits(gb, 2);
            sps->intra_boundary_filtering_disabled_flag = get_bits1(gb);
        }
    }

    // Inferred parameters
    sps->log2_ctb_size = sps->log2_min_cb_size +
                         sps->log2_diff_max_min_coding_block_size;
    sps->log2_min_pu_size = sps->log2_min_cb_size - 1;

    if (sps->log2_ctb_size > HEVC_MAX_LOG2_CTB_SIZE) {
        h265_err("CTB size out of range: 2^%d\n", sps->log2_ctb_size);
        return -EINVALDATA;
    }
    if (sps->log2_ctb_size < 4) {
        h265_err("log2_ctb_size %d differs from the bounds of any known profile\n",
               sps->log2_ctb_size);
        return -EINVALDATA;
    }

    sps->width = sps->pic_width_in_luma_samples;
    sps->height = sps->pic_height_in_luma_samples;
    sps->nb_st_rps = sps->num_short_term_ref_pic_sets;

    sps->ctb_width  = (sps->width  + (1 << sps->log2_ctb_size) - 1) >> sps->log2_ctb_size;
    sps->ctb_height = (sps->height + (1 << sps->log2_ctb_size) - 1) >> sps->log2_ctb_size;
    sps->ctb_size   = sps->ctb_width * sps->ctb_height;

    sps->min_cb_width  = sps->width  >> sps->log2_min_cb_size;
    sps->min_cb_height = sps->height >> sps->log2_min_cb_size;
    sps->min_tb_width  = sps->width  >> sps->log2_min_tb_size;
    sps->min_tb_height = sps->height >> sps->log2_min_tb_size;
    sps->min_pu_width  = sps->width  >> sps->log2_min_pu_size;
    sps->min_pu_height = sps->height >> sps->log2_min_pu_size;
    sps->tb_mask       = (1 << (sps->log2_ctb_size - sps->log2_min_tb_size)) - 1;

    sps->qp_bd_offset = 6 * (sps->bit_depth - 8);

    s->sps_list[sps_id] = *sps;
    h2645_rbsp_trailing_bits(gb);

	return 0;
}

static int pps_range_extension(struct bitstream *gb,
                               struct hevc_pps *pps, const struct hevc_sps *sps)
{
    int i;
    (void)sps;

    if (pps->transform_skip_enabled_flag)
        pps->log2_max_transform_skip_block_size = get_ue_golomb_31(gb) + 2;
    pps->cross_component_prediction_enabled_flag = get_bits1(gb);
    pps->chroma_qp_offset_list_enabled_flag = get_bits1(gb);

    if (pps->chroma_qp_offset_list_enabled_flag) {
        pps->diff_cu_chroma_qp_offset_depth = get_ue_golomb_31(gb);
        pps->chroma_qp_offset_list_len_minus1 = get_ue_golomb_31(gb);
        if (pps->chroma_qp_offset_list_len_minus1 > 5) {
            h265_err("chroma_qp_offset_list_len_minus1 shall be in the range [0, 5].\n");
            return -EINVALDATA;
        }
        for (i = 0; i <= pps->chroma_qp_offset_list_len_minus1; i++) {
            pps->cb_qp_offset_list[i] = get_se_golomb(gb);
            if (pps->cb_qp_offset_list[i]) {
                h265_wrn("cb_qp_offset_list not tested yet.\n");
            }
            pps->cr_qp_offset_list[i] = get_se_golomb(gb);
            if (pps->cr_qp_offset_list[i]) {
                h265_wrn("cb_qp_offset_list not tested yet.\n");
            }
        }
    }
    pps->log2_sao_offset_scale_luma = get_ue_golomb_31(gb);
    pps->log2_sao_offset_scale_chroma = get_ue_golomb_31(gb);

    return 0;
}

static int pps_scc_extension(struct bitstream *gb,
                             struct hevc_pps *pps, const struct hevc_sps *sps)
{
    int i, comp, num_comps, ret;

    pps->pps_curr_pic_ref_enabled_flag = get_bits1(gb);
    pps->residual_adaptive_colour_transform_enabled_flag = get_bits1(gb);
    if (pps->residual_adaptive_colour_transform_enabled_flag) {
        pps->pps_slice_act_qp_offsets_present_flag = get_bits1(gb);
        pps->pps_act_y_qp_offset  = get_se_golomb(gb) - 5;
        pps->pps_act_cb_qp_offset = get_se_golomb(gb) - 5;
        pps->pps_act_cr_qp_offset = get_se_golomb(gb) - 3;

#define CHECK_QP_OFFSET(name) (pps->pps_act_ ## name ## _qp_offset <= -12 || \
                               pps->pps_act_ ## name ## _qp_offset >= 12)
        ret = CHECK_QP_OFFSET(y) || CHECK_QP_OFFSET(cb) || CHECK_QP_OFFSET(cr);
#undef CHECK_QP_OFFSET
        if (ret) {
            h265_err("PpsActQpOffsetY/Cb/Cr shall be in the range of [-12, 12].\n");
            return -EINVALDATA;
        }
    }

    pps->pps_palette_predictor_initializer_present_flag = get_bits1(gb);
    if (pps->pps_palette_predictor_initializer_present_flag) {
        pps->pps_num_palette_predictor_initializer = get_ue_golomb(gb);
        if (pps->pps_num_palette_predictor_initializer > 0) {
            if (pps->pps_num_palette_predictor_initializer > HEVC_MAX_PALETTE_PREDICTOR_SIZE) {
                h265_err("pps_num_palette_predictor_initializer out of range: %u\n",
                       pps->pps_num_palette_predictor_initializer);
                return -EINVALDATA;
            }
            pps->monochrome_palette_flag = get_bits1(gb);
            pps->luma_bit_depth_entry = get_ue_golomb_31(gb) + 8;
            if (pps->luma_bit_depth_entry != sps->bit_depth)
                return -EINVALDATA;
            if (!pps->monochrome_palette_flag) {
                pps->chroma_bit_depth_entry = get_ue_golomb_31(gb) + 8;
                if (pps->chroma_bit_depth_entry != sps->bit_depth_chroma)
                    return -EINVALDATA;
            }

            num_comps = pps->monochrome_palette_flag ? 1 : 3;
            for (comp = 0; comp < num_comps; comp++) {
                int bit_depth = !comp ? pps->luma_bit_depth_entry : pps->chroma_bit_depth_entry;
                for (i = 0; i < pps->pps_num_palette_predictor_initializer; i++)
                    pps->pps_palette_predictor_initializer[comp][i] = get_bits(gb, bit_depth);
            }
        }
    }

    return 0;
}

static int pps_3d_extension(struct bitstream *gb,
                            struct hevc_pps *pps, const struct hevc_sps *sps)
{
    (void)gb;
    (void)pps;
    (void)sps;
    h265_err("patch welcome\n");
    return -1;
}

static int pps_multilayer_extension(struct bitstream *gb,
                                    struct hevc_pps *pps, const struct hevc_sps *sps)
{
    (void)gb;
    (void)pps;
    (void)sps;
    h265_err("patch welcome\n");
    return -1;
}

static int h265_decode_nal_pps(struct h265_context *s, struct hevc_pps *pps)
{
    struct bitstream *gb = &s->gb;
    const struct hevc_sps *sps = NULL;
    int i, ret = 0;
    unsigned int pps_id = 0;
    unsigned log2_parallel_merge_level_minus2;

    pps_id = pps->pps_pic_parameter_set_id = get_ue_golomb_long(gb);
    if (pps_id >= HEVC_MAX_PPS_COUNT) {
        h265_err("PPS id out of range: %d\n", pps_id);
        ret = -EINVALDATA;
        goto err;
    }
    pps->sps_id = get_ue_golomb_long(gb);
    if (pps->sps_id >= HEVC_MAX_SPS_COUNT) {
        h265_err("SPS id out of range: %d\n", pps->sps_id);
        ret = -EINVALDATA;
        goto err;
    }
#if 0
    if (!s->sps_list[pps->sps_id]) {
        h265_err("SPS %u does not exist.\n", pps->sps_id);
        ret = -EINVALDATA;
        goto err;
    }
#endif
    sps = &s->sps_list[pps->sps_id];

    pps->dependent_slice_segments_enabled_flag = get_bits1(gb);
    pps->output_flag_present_flag              = get_bits1(gb);
    pps->num_extra_slice_header_bits           = get_bits(gb, 3);

    pps->sign_data_hiding_enabled_flag = get_bits1(gb);
    pps->cabac_init_present_flag       = get_bits1(gb);

    pps->num_ref_idx_l0_default_active = get_ue_golomb_31(gb) + 1;
    pps->num_ref_idx_l1_default_active = get_ue_golomb_31(gb) + 1;
    if (pps->num_ref_idx_l0_default_active >= HEVC_MAX_REFS ||
        pps->num_ref_idx_l1_default_active >= HEVC_MAX_REFS) {
        h265_err("Too many default refs in PPS: %d/%d.\n",
               pps->num_ref_idx_l0_default_active, pps->num_ref_idx_l1_default_active);
        goto err;
    }

    pps->pic_init_qp_minus26 = get_se_golomb(gb);

    pps->constrained_intra_pred_flag = get_bits1(gb);
    pps->transform_skip_enabled_flag = get_bits1(gb);

    pps->cu_qp_delta_enabled_flag = get_bits1(gb);
    pps->diff_cu_qp_delta_depth   = 0;
    if (pps->cu_qp_delta_enabled_flag)
        pps->diff_cu_qp_delta_depth = get_ue_golomb_long(gb);

    if (pps->diff_cu_qp_delta_depth > sps->log2_diff_max_min_coding_block_size) {
        h265_err("diff_cu_qp_delta_depth %d is invalid\n",
               pps->diff_cu_qp_delta_depth);
        ret = -EINVALDATA;
        goto err;
    }

    pps->pps_cb_qp_offset = get_se_golomb(gb);
    if (pps->pps_cb_qp_offset < -12 || pps->pps_cb_qp_offset > 12) {
        h265_err("pps_cb_qp_offset out of range: %d\n", pps->pps_cb_qp_offset);
        ret = -EINVALDATA;
        goto err;
    }
    pps->pps_cr_qp_offset = get_se_golomb(gb);
    if (pps->pps_cr_qp_offset < -12 || pps->pps_cr_qp_offset > 12) {
        h265_err("pps_cr_qp_offset out of range: %d\n", pps->pps_cr_qp_offset);
        ret = -EINVALDATA;
        goto err;
    }
    pps->pps_slice_chroma_qp_offsets_present_flag = get_bits1(gb);

    pps->weighted_pred_flag   = get_bits1(gb);
    pps->weighted_bipred_flag = get_bits1(gb);

    pps->transquant_bypass_enabled_flag   = get_bits1(gb);
    pps->tiles_enabled_flag               = get_bits1(gb);
    pps->entropy_coding_sync_enabled_flag = get_bits1(gb);
    if (pps->tiles_enabled_flag) {
        int num_tile_columns_minus1 = get_ue_golomb(gb);
        int num_tile_rows_minus1    = get_ue_golomb(gb);

        if (num_tile_columns_minus1 < 0 ||
            num_tile_columns_minus1 >= sps->ctb_width) {
            h265_err("num_tile_columns_minus1 out of range: %d\n",
                   num_tile_columns_minus1);
            ret = num_tile_columns_minus1 < 0 ? num_tile_columns_minus1 : -EINVALDATA;
            goto err;
        }
        if (num_tile_rows_minus1 < 0 ||
            num_tile_rows_minus1 >= sps->ctb_height) {
            h265_err("num_tile_rows_minus1 out of range: %d\n",
                   num_tile_rows_minus1);
            ret = num_tile_rows_minus1 < 0 ? num_tile_rows_minus1 : -EINVALDATA;
            goto err;
        }
        pps->num_tile_columns = num_tile_columns_minus1 + 1;
        pps->num_tile_rows    = num_tile_rows_minus1    + 1;

        pps->uniform_spacing_flag = get_bits1(gb);
        if (!pps->uniform_spacing_flag) {
            uint64_t sum = 0;
            for (i = 0; i < pps->num_tile_columns - 1; i++) {
                pps->column_width[i] = get_ue_golomb_long(gb) + 1;
                sum                 += pps->column_width[i];
            }
            if (sum >= sps->ctb_width) {
                h265_err("Invalid tile widths.\n");
                ret = -EINVALDATA;
                goto err;
            }
            pps->column_width[pps->num_tile_columns - 1] = sps->ctb_width - sum;

            sum = 0;
            for (i = 0; i < pps->num_tile_rows - 1; i++) {
                pps->row_height[i] = get_ue_golomb_long(gb) + 1;
                sum               += pps->row_height[i];
            }
            if (sum >= sps->ctb_height) {
                h265_err("Invalid tile heights.\n");
                ret = -EINVALDATA;
                goto err;
            }
            pps->row_height[pps->num_tile_rows - 1] = sps->ctb_height - sum;
        }
        pps->loop_filter_across_tiles_enabled_flag = get_bits1(gb);
    }

    pps->pps_loop_filter_across_slices_enabled_flag = get_bits1(gb);

    pps->deblocking_filter_control_present_flag = get_bits1(gb);
    if (pps->deblocking_filter_control_present_flag) {
        pps->deblocking_filter_override_enabled_flag = get_bits1(gb);
        pps->pps_deblocking_filter_disabled_flag     = get_bits1(gb);
        if (!pps->pps_deblocking_filter_disabled_flag) {
            int beta_offset_div2 = get_se_golomb(gb);
            int tc_offset_div2   = get_se_golomb(gb) ;
            if (beta_offset_div2 < -6 || beta_offset_div2 > 6) {
                h265_err("pps_beta_offset_div2 out of range: %d\n",
                       beta_offset_div2);
                ret = -EINVALDATA;
                goto err;
            }
            if (tc_offset_div2 < -6 || tc_offset_div2 > 6) {
                h265_err("pps_tc_offset_div2 out of range: %d\n",
                       tc_offset_div2);
                ret = -EINVALDATA;
                goto err;
            }
            pps->pps_beta_offset = 2 * beta_offset_div2;
            pps->pps_tc_offset   = 2 *   tc_offset_div2;
        }
    }

    pps->pps_scaling_list_data_present_flag = get_bits1(gb);
    if (pps->pps_scaling_list_data_present_flag) {
        set_default_scaling_list_data(&pps->scaling_list);
        ret = hevc_decode_scaling_list(gb, &pps->scaling_list, sps);
        if (ret < 0)
            goto err;
    }
    pps->lists_modification_present_flag = get_bits1(gb);
    log2_parallel_merge_level_minus2     = get_ue_golomb_long(gb);
    if (log2_parallel_merge_level_minus2 > sps->log2_ctb_size) {
        h265_err("log2_parallel_merge_level_minus2 out of range: %d\n",
               log2_parallel_merge_level_minus2);
        ret = -EINVALDATA;
        goto err;
    }
    pps->log2_parallel_merge_level       = log2_parallel_merge_level_minus2 + 2;

    pps->slice_segment_header_extension_present_flag = get_bits1(gb);
    pps->pps_extension_present_flag = get_bits1(gb);
    if (pps->pps_extension_present_flag) {
        pps->pps_range_extension_flag     = get_bits1(gb);
        pps->pps_multilayer_extension_flag = get_bits1(gb);
        pps->pps_3d_extension_flag         = get_bits1(gb);
        pps->pps_scc_extension_flag        = get_bits1(gb);
        skip_bits(gb, 4); // pps_extension_4bits

        if (pps->pps_range_extension_flag) {
            if ((ret = pps_range_extension(gb, pps, sps)) < 0)
                goto err;
        }

        if (pps->pps_multilayer_extension_flag) {
            if ((ret = pps_multilayer_extension(gb, pps, sps)) < 0)
                goto err;
        }

        if (pps->pps_3d_extension_flag) {
            if ((ret = pps_3d_extension(gb, pps, sps)) < 0)
                goto err;
        }

        if (pps->pps_scc_extension_flag) {
            if ((ret = pps_scc_extension(gb, pps, sps)) < 0)
                goto err;
        }
    }

    s->pps_list[pps_id] = *pps;
    h2645_rbsp_trailing_bits(gb);

err:
    return ret;
}

static int h265_decode_nal_sei(struct bitstream *gb)
{
	while (h2645_more_rbsp_data(gb))
			skip_bits1(gb); /* XXX */
	h2645_rbsp_trailing_bits(gb);
	return 0;
}

static int hevc_compute_poc(const struct hevc_sps *sps,
                            int pocTid0, int poc_lsb, int nal_unit_type)
{
    int max_poc_lsb  = 1 << sps->log2_max_poc_lsb;
    int prev_poc_lsb = pocTid0 % max_poc_lsb;
    int prev_poc_msb = pocTid0 - prev_poc_lsb;
    int poc_msb;

    if (poc_lsb < prev_poc_lsb && prev_poc_lsb - poc_lsb >= max_poc_lsb / 2)
        poc_msb = prev_poc_msb + max_poc_lsb;
    else if (poc_lsb > prev_poc_lsb && poc_lsb - prev_poc_lsb > max_poc_lsb / 2)
        poc_msb = prev_poc_msb - max_poc_lsb;
    else
        poc_msb = prev_poc_msb;

    // For BLA picture types, POCmsb is set to 0.
    if (nal_unit_type == HEVC_NAL_BLA_W_LP   ||
        nal_unit_type == HEVC_NAL_BLA_W_RADL ||
        nal_unit_type == HEVC_NAL_BLA_N_LP)
        poc_msb = 0;

    return poc_msb + poc_lsb;
}

static int hevc_frame_nb_refs(struct hevc_slice_header *sh,
                              const struct hevc_pps *pps)
{
    const struct hevc_short_term_rps *rps = sh->short_term_rps;
    const struct hevc_long_term_rps *long_rps = &sh->long_term_rps;
    int ret = 0;
    int i;

    if (rps) {
        for (i = 0; i < rps->num_negative_pics; i++)
            ret += !!rps->used[i];
        for (; i < rps->num_delta_pocs; i++)
            ret += !!rps->used[i];
    }

    if (long_rps) {
        for (i = 0; i < long_rps->nb_refs; i++)
            ret += !!long_rps->used[i];
    }

    if (pps->pps_curr_pic_ref_enabled_flag)
        ret++;

    return ret;
}

static int hevc_pred_weight_table(struct bitstream *gb,
                          struct hevc_slice_header *sh, const struct hevc_sps *sps)
{
    int i = 0;
    int j = 0;
    int luma_log2_weight_denom;
    int chroma = !sps->separate_colour_plane_flag &&
                  sps->chroma_format_idc != 0;
    sh->has_chroma_weights = chroma;

    luma_log2_weight_denom = get_ue_golomb_long(gb);
    if (luma_log2_weight_denom < 0 || luma_log2_weight_denom > 7) {
        h265_err("luma_log2_weight_denom %d is invalid\n", luma_log2_weight_denom);
        return -EINVALDATA;
    }
    sh->luma_log2_weight_denom = av_clip_uintp2(luma_log2_weight_denom, 3);
    if (chroma) {
        int64_t chroma_log2_weight_denom;
        sh->delta_chroma_log2_weight_denom = (int64_t)get_se_golomb(gb);
        chroma_log2_weight_denom = luma_log2_weight_denom +
                                   sh->delta_chroma_log2_weight_denom;
        if (chroma_log2_weight_denom < 0 || chroma_log2_weight_denom > 7) {
            h265_err("chroma_log2_weight_denom %"PRId64" is invalid\n",
                      chroma_log2_weight_denom);
            return -EINVALDATA;
        }
        sh->chroma_log2_weight_denom = chroma_log2_weight_denom;
    }

    for (i = 0; i < sh->nb_refs[L0]; i++) {
        sh->luma_weight_l0_flag[i] = get_bits1(gb);
        if (!sh->luma_weight_l0_flag[i]) {
            sh->delta_luma_weight_l0[i] = 0;
            sh->luma_weight_l0[i] = 1 << sh->luma_log2_weight_denom;
            sh->luma_offset_l0[i] = 0;
        }
    }
    if (chroma) {
        for (i = 0; i < sh->nb_refs[L0]; i++)
            sh->chroma_weight_l0_flag[i] = get_bits1(gb);
    } else {
        for (i = 0; i < sh->nb_refs[L0]; i++)
            sh->chroma_weight_l0_flag[i] = 0;
    }

    for (i = 0; i < sh->nb_refs[L0]; i++) {
        if (sh->luma_weight_l0_flag[i]) {
            sh->delta_luma_weight_l0[i] = get_se_golomb(gb);
            if ((int8_t)sh->delta_luma_weight_l0[i] != sh->delta_luma_weight_l0[i])
                return -EINVALDATA;
            sh->luma_weight_l0[i] = (1 << sh->luma_log2_weight_denom) +
                                    sh->delta_luma_weight_l0[i];
            sh->luma_offset_l0[i] = get_se_golomb(gb);
            if (sh->luma_offset_l0[i] < -(1 << (sps->bit_depth - 1)) ||
                sh->luma_offset_l0[i] > ((1 << (sps->bit_depth - 1)) - 1)) {
                return -EINVALDATA;
            }
        }
        if (sh->chroma_weight_l0_flag[i]) {
            for (j = 0; j < 2; j++) {
                sh->delta_chroma_weight_l0[i][j] = get_se_golomb(gb);
                sh->delta_chroma_offset_l0[i][j] = get_se_golomb(gb);
                if ((int8_t)sh->delta_chroma_weight_l0[i][j] != sh->delta_chroma_weight_l0[i][j] ||
                    sh->delta_chroma_offset_l0[i][j] < -(4 << (sps->bit_depth - 1)) ||
                    sh->delta_chroma_offset_l0[i][j] > ((4 << (sps->bit_depth - 1)) - 1)) {
                    return -EINVALDATA;
                }
                sh->chroma_weight_l0[i][j] = (1 << sh->chroma_log2_weight_denom) +
                                              sh->delta_chroma_weight_l0[i][j];
                sh->chroma_offset_l0[i][j] = av_clip((sh->delta_chroma_offset_l0[i][j] - ((128 * sh->chroma_weight_l0[i][j]) >> sh->chroma_log2_weight_denom) + 128), -128, 127);
            }
        } else {
            for (j = 0; j < 2; j++) {
                sh->delta_chroma_weight_l0[i][j] = 0;
                sh->delta_chroma_offset_l0[i][j] = 0;
                sh->chroma_weight_l0[i][j] = 1 << sh->chroma_log2_weight_denom;
                sh->chroma_offset_l0[i][j] = 0;
            }
        }
    }

    if (sh->slice_type == HEVC_SLICE_B) {
        for (i = 0; i < sh->nb_refs[L1]; i++) {
            sh->luma_weight_l1_flag[i] = get_bits1(gb);
            if (!sh->luma_weight_l1_flag[i]) {
                sh->luma_weight_l1[i] = 1 << sh->luma_log2_weight_denom;
                sh->luma_offset_l1[i] = 0;
            }
        }
        if (chroma) {
            for (i = 0; i < sh->nb_refs[L1]; i++)
                sh->chroma_weight_l1_flag[i] = get_bits1(gb);
        } else {
            for (i = 0; i < sh->nb_refs[L1]; i++)
                sh->chroma_weight_l1_flag[i] = 0;
        }

        for (i = 0; i < sh->nb_refs[L1]; i++) {
            if (sh->luma_weight_l1_flag[i]) {
                int delta_luma_weight_l1 = get_se_golomb(gb);
                if ((int8_t)delta_luma_weight_l1 != delta_luma_weight_l1)
                    return -EINVALDATA;
                sh->luma_weight_l1[i] = (1 << sh->luma_log2_weight_denom)
                                        + delta_luma_weight_l1;
                sh->luma_offset_l1[i] = get_se_golomb(gb);
            }
            if (sh->chroma_weight_l1_flag[i]) {
                for (j = 0; j < 2; j++) {
                    sh->delta_chroma_weight_l1[i][j] = get_se_golomb(gb);
                    sh->delta_chroma_offset_l1[i][j] = get_se_golomb(gb);
                    if ((int8_t)sh->delta_chroma_weight_l1[i][j] != sh->delta_chroma_weight_l1[i][j] ||
                        sh->delta_chroma_offset_l1[i][j] < -(4 << (sps->bit_depth - 1)) ||
                        sh->delta_chroma_offset_l1[i][j] > ((4 << (sps->bit_depth - 1)) - 1)) {
                        return -EINVALDATA;
                    }

                    sh->chroma_weight_l1[i][j] = (1 << sh->chroma_log2_weight_denom) +
                                                  sh->delta_chroma_weight_l1[i][j];
                    sh->chroma_offset_l1[i][j] = av_clip((sh->delta_chroma_offset_l1[i][j] - ((128 * sh->chroma_weight_l1[i][j]) >> sh->chroma_log2_weight_denom) + 128), -128, 127);
                }
            } else {
                for (j = 0; j < 2; j++) {
                    sh->delta_chroma_weight_l1[i][j] = 0;
                    sh->delta_chroma_offset_l1[i][j] = 0;
                    sh->chroma_weight_l1[i][j] = 1 << sh->chroma_log2_weight_denom;
                    sh->chroma_offset_l1[i][j] = 0;
                }
            }
        }
    }

    return 0;
}

static int hevc_decode_slice_header(struct h265_context *s, struct hevc_slice_header *sh)
{
    struct bitstream *gb = &s->gb;
    struct hevc_pps *pps = NULL;
    struct hevc_sps *sps = NULL;
    int i, ret;

    sh->first_slice_segment_in_pic_flag = get_bits1(gb);
    sh->no_output_of_prior_pics_flag = 0;
    if (IS_IRAP(s))
        sh->no_output_of_prior_pics_flag = get_bits1(gb);

    sh->pps_id = get_ue_golomb_long(gb);
    if (sh->pps_id >= HEVC_MAX_PPS_COUNT) {
        h265_err("PPS id out of range: %d\n", sh->pps_id);
        return -EINVALDATA;
    }

    pps = &s->pps_list[sh->pps_id];
    sps = &s->sps_list[pps->sps_id];

    sh->dependent_slice_segment_flag = 0;
    if (!sh->first_slice_segment_in_pic_flag) {
        int slice_address_length;

        if (pps->dependent_slice_segments_enabled_flag)
            sh->dependent_slice_segment_flag = get_bits1(gb);

        slice_address_length = clog2(sps->ctb_width * sps->ctb_height);
        sh->slice_segment_address = get_bits(gb, slice_address_length);
        if (sh->slice_segment_address >= sps->ctb_width * sps->ctb_height) {
            h265_err("Invalid slice segment address: %u.\n",  sh->slice_segment_address);
            return -EINVALDATA;
        }
    }

    if (!sh->dependent_slice_segment_flag) {
        for (i = 0; i < pps->num_extra_slice_header_bits; i++)
            skip_bits(gb, 1);  // slice_reserved_undetermined_flag[i]

        sh->slice_type = get_ue_golomb_long(gb);
        if (!(sh->slice_type == HEVC_SLICE_I ||
              sh->slice_type == HEVC_SLICE_P ||
              sh->slice_type == HEVC_SLICE_B)) {
            h265_err("Unknown slice type: %d.\n",
                   sh->slice_type);
            return -EINVALDATA;
        }
        if (IS_IRAP(s) && sh->slice_type != HEVC_SLICE_I &&
            !pps->pps_curr_pic_ref_enabled_flag) {
            h265_err("Inter slices in an IRAP frame.\n");
            return -EINVALDATA;
        }

        // when flag is not present, picture is inferred to be output
        sh->pic_output_flag = 1;
        if (pps->output_flag_present_flag)
            sh->pic_output_flag = get_bits1(gb);

        if (sps->separate_colour_plane_flag)
            sh->colour_plane_id = get_bits(gb, 2);

        if (!IS_IDR(s)) {
            int poc, pos;
            sh->pic_order_cnt_lsb = get_bits(gb, sps->log2_max_poc_lsb);
            poc = hevc_compute_poc(sps, s->pocTid0, sh->pic_order_cnt_lsb, s->nal_unit_type);
            if (!sh->first_slice_segment_in_pic_flag && poc != s->poc) {
                h265_wrn("Ignoring POC change between slices: %d -> %d\n", s->poc, poc);
                poc = s->poc;
            }
            s->poc = poc;

            sh->short_term_ref_pic_set_sps_flag = get_bits1(gb);
            pos = get_bits_pos(gb);
            if (!sh->short_term_ref_pic_set_sps_flag) {
                ret = hevc_decode_st_rps(gb, &sh->slice_rps, sps, 1);
                if (ret < 0)
                    return ret;

                sh->short_term_rps = &sh->slice_rps;
            } else {
                int numbits, rps_idx;

                if (!sps->nb_st_rps) {
                    h265_err("No ref lists in the SPS.\n");
                    return -EINVALDATA;
                }

                numbits = clog2(sps->nb_st_rps);
                rps_idx = numbits > 0 ? get_bits(gb, numbits) : 0;
                sh->short_term_ref_pic_set_idx = rps_idx;
                sh->short_term_rps = &sps->st_rps[rps_idx];
            }
            sh->short_term_ref_pic_set_size = get_bits_pos(gb) - pos;

            pos = get_bits_pos(gb);
            ret = hevc_decode_lt_rps(gb, &sh->long_term_rps, sps, s);
            if (ret < 0) {
                h265_err("Invalid long term RPS.\n");
                return -EINVALDATA;
            }
            sh->long_term_ref_pic_set_size = get_bits_pos(gb) - pos;

            if (sps->sps_temporal_mvp_enabled_flag)
                sh->slice_temporal_mvp_enabled_flag = get_bits1(gb);
            else
                sh->slice_temporal_mvp_enabled_flag = 0;
        } else {
            s->poc                              = 0;
            sh->pic_order_cnt_lsb               = 0;
            sh->short_term_ref_pic_set_sps_flag = 0;
            sh->short_term_ref_pic_set_size     = 0;
            sh->short_term_rps                  = NULL;
            sh->long_term_ref_pic_set_size      = 0;
            sh->slice_temporal_mvp_enabled_flag = 0;
        }

        /* 8.3.1 */
        if (sh->first_slice_segment_in_pic_flag && s->temporal_id == 0 &&
            s->nal_unit_type != HEVC_NAL_TRAIL_N &&
            s->nal_unit_type != HEVC_NAL_TSA_N   &&
            s->nal_unit_type != HEVC_NAL_STSA_N  &&
            s->nal_unit_type != HEVC_NAL_RADL_N  &&
            s->nal_unit_type != HEVC_NAL_RADL_R  &&
            s->nal_unit_type != HEVC_NAL_RASL_N  &&
            s->nal_unit_type != HEVC_NAL_RASL_R)
            s->pocTid0 = s->poc;

        if (sps->sample_adaptive_offset_enabled_flag) {
            sh->slice_sao_luma_flag = get_bits1(gb);
            if (!sps->separate_colour_plane_flag && sps->chroma_format_idc) {
                sh->slice_sao_chroma_flag = get_bits1(gb);
            }
        } else {
            sh->slice_sao_luma_flag = 0;
            sh->slice_sao_chroma_flag = 0;
        }

        sh->num_ref_idx_l0_active = sh->num_ref_idx_l1_active = 0;
        sh->nb_refs[L0] = sh->nb_refs[L1] = 0;
        if (sh->slice_type == HEVC_SLICE_P || sh->slice_type == HEVC_SLICE_B) {
            int nb_refs;

            sh->num_ref_idx_l0_active = pps->num_ref_idx_l0_default_active;
            if (sh->slice_type == HEVC_SLICE_B)
                sh->num_ref_idx_l1_active = pps->num_ref_idx_l1_default_active;

            sh->num_ref_idx_active_override_flag = get_bits1(gb);
            if (sh->num_ref_idx_active_override_flag) {
                sh->num_ref_idx_l0_active = get_ue_golomb_31(gb) + 1;
                if (sh->slice_type == HEVC_SLICE_B)
                    sh->num_ref_idx_l1_active = get_ue_golomb_31(gb) + 1;
            }

            sh->nb_refs[L0] = sh->num_ref_idx_l0_active;
            sh->nb_refs[L1] = sh->num_ref_idx_l1_active;
            if (sh->nb_refs[L0] >= HEVC_MAX_REFS || sh->nb_refs[L1] >= HEVC_MAX_REFS) {
                h265_err("Too many refs: %d/%d.\n", sh->nb_refs[L0], sh->nb_refs[L1]);
                return -EINVALDATA;
            }

            sh->ref_pic_list_modification_flag_l0 = sh->ref_pic_list_modification_flag_l1 = 0;
            sh->rpl_modification_flag[0] = sh->rpl_modification_flag[1] = 0;
            nb_refs = hevc_frame_nb_refs(sh, pps);
            if (!nb_refs) {
                h265_err("Zero refs for a frame with P or B slices\n");
                return -EINVALDATA;
            }
            if (pps->lists_modification_present_flag && nb_refs > 1) {
                sh->ref_pic_list_modification_flag_l0 = get_bits1(gb);
                if (sh->ref_pic_list_modification_flag_l0) {
                    for (i = 0; i < sh->nb_refs[L0]; i++)
                        sh->list_entry_lx[0][i] = get_bits(gb, clog2(nb_refs));
                }

                if (sh->slice_type == HEVC_SLICE_B) {
                    sh->ref_pic_list_modification_flag_l1 = get_bits1(gb);
                    if (sh->ref_pic_list_modification_flag_l1 == 1)
                        for (i = 0; i < sh->nb_refs[L1]; i++)
                            sh->list_entry_lx[1][i] = get_bits(gb, clog2(nb_refs));
                }
            }
            sh->rpl_modification_flag[0] = sh->ref_pic_list_modification_flag_l0;
            sh->rpl_modification_flag[1] = sh->ref_pic_list_modification_flag_l1;

            if (sh->slice_type == HEVC_SLICE_B)
                sh->mvd_l1_zero_flag = get_bits1(gb);

            if (pps->cabac_init_present_flag)
                sh->cabac_init_flag = get_bits1(gb);
            else
                sh->cabac_init_flag = 0;

            sh->collocated_ref_idx = 0;
            if (sh->slice_temporal_mvp_enabled_flag) {
                if (sh->slice_type == HEVC_SLICE_B)
                    sh->collocated_from_l0_flag = get_bits1(gb);
                else
                    sh->collocated_from_l0_flag = 1;

                if (sh->collocated_from_l0_flag) {
                    if (sh->num_ref_idx_l0_active > 1)
                        sh->collocated_ref_idx = get_ue_golomb_long(gb);
                    else
                        sh->collocated_ref_idx = 0;
                }
                else {
                    if (sh->num_ref_idx_l1_active > 1)
                        sh->collocated_ref_idx = get_ue_golomb_long(gb);
                    else
                        sh->collocated_ref_idx = 0;
                }

                if (sh->collocated_ref_idx >= sh->nb_refs[!sh->collocated_from_l0_flag]) {
                    h265_wrn("Invalid collocated_ref_idx: %d vs. nb_refs: %d\n",
                             sh->collocated_ref_idx, sh->nb_refs[!sh->collocated_from_l0_flag]);
                    return -EINVALDATA;
                }
            }

            sh->has_luma_weights   = ((pps->weighted_pred_flag   && sh->slice_type == HEVC_SLICE_P) ||
                                     (pps->weighted_bipred_flag && sh->slice_type == HEVC_SLICE_B));
            sh->has_chroma_weights = 0;
            if (sh->has_luma_weights) {
                int ret = hevc_pred_weight_table(gb, sh, sps);
                if (ret < 0)
                    return ret;
            }

            sh->max_num_merge_cand = 5 - get_ue_golomb_long(gb);
            if (sh->max_num_merge_cand < 1 || sh->max_num_merge_cand > 5) {
                h265_err("Invalid number of merging MVP candidates: %d.\n",
                         sh->max_num_merge_cand);
                return -EINVALDATA;
            }

            // Syntax in 7.3.6.1
            if (sps->motion_vector_resolution_control_idc == 2)
                sh->use_integer_mv_flag = get_bits1(gb);
            else
                // Inferred to be equal to motion_vector_resolution_control_idc if not present
                sh->use_integer_mv_flag = sps->motion_vector_resolution_control_idc;
        }

        sh->slice_qp_delta = get_se_golomb(gb);

        if (pps->pps_slice_chroma_qp_offsets_present_flag) {
            sh->slice_cb_qp_offset = get_se_golomb(gb);
            sh->slice_cr_qp_offset = get_se_golomb(gb);
            if (sh->slice_cb_qp_offset < -12 || sh->slice_cb_qp_offset > 12 ||
                sh->slice_cr_qp_offset < -12 || sh->slice_cr_qp_offset > 12) {
                h265_err("Invalid slice cx qp offset.\n");
                return -EINVALDATA;
            }
        } else {
            sh->slice_cb_qp_offset = 0;
            sh->slice_cr_qp_offset = 0;
        }

        if (pps->pps_slice_act_qp_offsets_present_flag) {
            sh->slice_act_y_qp_offset  = get_se_golomb(gb);
            sh->slice_act_cb_qp_offset = get_se_golomb(gb);
            sh->slice_act_cr_qp_offset = get_se_golomb(gb);
        }
        else {
            sh->slice_act_y_qp_offset  = 0;
            sh->slice_act_cb_qp_offset = 0;
            sh->slice_act_cr_qp_offset = 0;
        }

        sh->cu_chroma_qp_offset_enabled_flag = 0;
        if (pps->chroma_qp_offset_list_enabled_flag)
            sh->cu_chroma_qp_offset_enabled_flag = get_bits1(gb);

        sh->deblocking_filter_override_flag = 0;
        if (pps->deblocking_filter_override_enabled_flag)
            sh->deblocking_filter_override_flag = get_bits1(gb);

        if (sh->deblocking_filter_override_flag) {
            sh->slice_deblocking_filter_disabled_flag = get_bits1(gb);
            if (!sh->slice_deblocking_filter_disabled_flag) {
                int beta_offset_div2 = get_se_golomb(gb);
                int tc_offset_div2   = get_se_golomb(gb) ;
                if (beta_offset_div2 < -6 || beta_offset_div2 > 6 ||
                    tc_offset_div2   < -6 || tc_offset_div2   > 6) {
                    h265_err("Invalid deblock filter offsets: %d, %d\n",
                        beta_offset_div2, tc_offset_div2);
                    return -EINVALDATA;
                }
                sh->slice_beta_offset = beta_offset_div2 * 2;
                sh->slice_tc_offset   = tc_offset_div2 * 2;
            } else {
                sh->slice_beta_offset = pps->pps_beta_offset;
                sh->slice_tc_offset   = pps->pps_tc_offset;
            }
        } else {
            sh->slice_deblocking_filter_disabled_flag = pps->pps_deblocking_filter_disabled_flag;
            sh->slice_beta_offset     = pps->pps_beta_offset;
            sh->slice_tc_offset       = pps->pps_tc_offset;
        }

        if (pps->pps_loop_filter_across_slices_enabled_flag &&
            (sh->slice_sao_luma_flag || sh->slice_sao_chroma_flag ||
            !sh->slice_deblocking_filter_disabled_flag))
            sh->slice_loop_filter_across_slices_enabled_flag = get_bits1(gb);
        else
            sh->slice_loop_filter_across_slices_enabled_flag =
                pps->pps_loop_filter_across_slices_enabled_flag;
    }

    sh->num_entry_point_offsets = 0;
    if (pps->tiles_enabled_flag || pps->entropy_coding_sync_enabled_flag) {
        sh->num_entry_point_offsets = get_ue_golomb_long(gb);
        if (sh->num_entry_point_offsets > HEVC_MAX_ENTRY_POINT_OFFSETS) {
            h265_err("Too many entry points: " "%"PRIu16".\n", sh->num_entry_point_offsets);
            return -EINVALDATA;
        }
        if (sh->num_entry_point_offsets > 0) {
            sh->offset_len = get_ue_golomb_long(gb) + 1;
            for (i = 0; i < sh->num_entry_point_offsets; i++)
                sh->entry_point_offset[i] = get_bits_long(gb, sh->offset_len) + 1;
        }
    }

    if (pps->slice_segment_header_extension_present_flag) {
        unsigned int length = get_ue_golomb_long(gb);
        for (i = 0; i < length; i++)
            skip_bits(gb, 8);  // slice_header_extension_data_byte
    }

	return 0;
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
	start_pos = get_bits_pos(gb);
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

	printf("H265 NAL [%s] {\n", h265_nal_unit_name(s->nal_unit_type));
	h265_field2("nal_unit_type", s->nal_unit_type, h265_nal_unit_name(s->nal_unit_type));
	h265_field("nuh_layer_id", s->nuh_layer_id);
	h265_field("temporal_id", s->temporal_id);

	switch (s->nal_unit_type) {
	case HEVC_NAL_VPS:
		err = hevc_decode_nal_vps(s, &s->tmp_vps);
		if (err < 0)
			goto exit;
        h265_print_nal_vps(&s->tmp_vps);
		break;
	case HEVC_NAL_SPS:
		err = h265_decode_nal_sps(s, &s->tmp_sps);
		if (err < 0)
			goto exit;
        h265_print_nal_sps(&s->tmp_sps);
		break;
	case HEVC_NAL_PPS:
		err = h265_decode_nal_pps(s, &s->tmp_pps);
		if (err < 0)
			goto exit;
        h265_print_nal_pps(&s->tmp_pps);
		break;
	case HEVC_NAL_SEI_PREFIX:
	case HEVC_NAL_SEI_SUFFIX:
		err = h265_decode_nal_sei(gb);
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
		err = hevc_decode_slice_header(s, &s->sh);
		if (err < 0)
			goto exit;
        end_pos = get_bits_pos(gb);
        h2645_rbsp_trailing_bits(gb); /* byte alignment */
        h265_print_nal_slice_header(s, &s->sh);
        h265_fieldl("slice_header_size", end_pos - start_pos);
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
