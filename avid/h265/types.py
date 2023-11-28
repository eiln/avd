#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

HEVC_NAL_TRAIL_N        = 0
HEVC_NAL_TRAIL_R        = 1
HEVC_NAL_TSA_N          = 2
HEVC_NAL_TSA_R          = 3
HEVC_NAL_STSA_N         = 4
HEVC_NAL_STSA_R         = 5
HEVC_NAL_RADL_N         = 6
HEVC_NAL_RADL_R         = 7
HEVC_NAL_RASL_N         = 8
HEVC_NAL_RASL_R         = 9
HEVC_NAL_VCL_N10        = 10
HEVC_NAL_VCL_R11        = 11
HEVC_NAL_VCL_N12        = 12
HEVC_NAL_VCL_R13        = 13
HEVC_NAL_VCL_N14        = 14
HEVC_NAL_VCL_R15        = 15
HEVC_NAL_BLA_W_LP       = 16
HEVC_NAL_BLA_W_RADL     = 17
HEVC_NAL_BLA_N_LP       = 18
HEVC_NAL_IDR_W_RADL     = 19
HEVC_NAL_IDR_N_LP       = 20
HEVC_NAL_CRA_NUT        = 21
HEVC_NAL_RSV_IRAP_VCL22 = 22
HEVC_NAL_RSV_IRAP_VCL23 = 23
HEVC_NAL_RSV_VCL24      = 24
HEVC_NAL_RSV_VCL25      = 25
HEVC_NAL_RSV_VCL26      = 26
HEVC_NAL_RSV_VCL27      = 27
HEVC_NAL_RSV_VCL28      = 28
HEVC_NAL_RSV_VCL29      = 29
HEVC_NAL_RSV_VCL30      = 30
HEVC_NAL_RSV_VCL31      = 31
HEVC_NAL_VPS            = 32
HEVC_NAL_SPS            = 33
HEVC_NAL_PPS            = 34
HEVC_NAL_AUD            = 35
HEVC_NAL_EOS_NUT        = 36
HEVC_NAL_EOB_NUT        = 37
HEVC_NAL_FD_NUT         = 38
HEVC_NAL_SEI_PREFIX     = 39
HEVC_NAL_SEI_SUFFIX     = 40
HEVC_NAL_RSV_NVCL41     = 41
HEVC_NAL_RSV_NVCL42     = 42
HEVC_NAL_RSV_NVCL43     = 43
HEVC_NAL_RSV_NVCL44     = 44
HEVC_NAL_RSV_NVCL45     = 45
HEVC_NAL_RSV_NVCL46     = 46
HEVC_NAL_RSV_NVCL47     = 47
HEVC_NAL_UNSPEC48       = 48
HEVC_NAL_UNSPEC49       = 49
HEVC_NAL_UNSPEC50       = 50
HEVC_NAL_UNSPEC51       = 51
HEVC_NAL_UNSPEC52       = 52
HEVC_NAL_UNSPEC53       = 53
HEVC_NAL_UNSPEC54       = 54
HEVC_NAL_UNSPEC55       = 55
HEVC_NAL_UNSPEC56       = 56
HEVC_NAL_UNSPEC57       = 57
HEVC_NAL_UNSPEC58       = 58
HEVC_NAL_UNSPEC59       = 59
HEVC_NAL_UNSPEC60       = 60
HEVC_NAL_UNSPEC61       = 61
HEVC_NAL_UNSPEC62       = 62
HEVC_NAL_UNSPEC63       = 63

HEVC_SLICE_B = 0
HEVC_SLICE_P = 1
HEVC_SLICE_I = 2

# // 7.4.3.1: vps_max_layers_minus1 is in [0, 62].
HEVC_MAX_LAYERS     = 63
# // 7.4.3.1: vps_max_sub_layers_minus1 is in [0, 6].
HEVC_MAX_SUB_LAYERS = 7
# // 7.4.3.1: vps_num_layer_sets_minus1 is in [0, 1023].
HEVC_MAX_LAYER_SETS = 1024

# // 7.4.2.1: vps_video_parameter_set_id is u(4).
HEVC_MAX_VPS_COUNT = 16
# // 7.4.3.2.1: sps_seq_parameter_set_id is in [0, 15].
HEVC_MAX_SPS_COUNT = 16
# // 7.4.3.3.1: pps_pic_parameter_set_id is in [0, 63].
HEVC_MAX_PPS_COUNT = 64

# // A.4.2: MaxDpbSize is bounded above by 16.
HEVC_MAX_DPB_SIZE = 16
# // 7.4.3.1: vps_max_dec_pic_buffering_minus1[i] is in [0, MaxDpbSize - 1].
HEVC_MAX_REFS     = HEVC_MAX_DPB_SIZE

# // 7.4.3.2.1: num_short_term_ref_pic_sets is in [0, 64].
HEVC_MAX_SHORT_TERM_REF_PIC_SETS = 64
# // 7.4.3.2.1: num_long_term_ref_pics_sps is in [0, 32].
HEVC_MAX_LONG_TERM_REF_PICS      = 32

# // A.3: all profiles require that CtbLog2SizeY is in [4, 6].
HEVC_MIN_LOG2_CTB_SIZE = 4
HEVC_MAX_LOG2_CTB_SIZE = 6

# // E.3.2: cpb_cnt_minus1[i] is in [0, 31].
HEVC_MAX_CPB_CNT = 32

# // A.4.1: in table A.6 the highest level allows a MaxLumaPs of 35 651 584.
HEVC_MAX_LUMA_PS = 35651584
# // A.4.1: pic_width_in_luma_samples and pic_height_in_luma_samples are
# // constrained to be not greater than sqrt(MaxLumaPs * 8).  Hence height/
# // width are bounded above by sqrt(8 * 35651584) = 16888.2 samples.
HEVC_MAX_WIDTH  = 16888
HEVC_MAX_HEIGHT = 16888

# // A.4.1: table A.6 allows at most 22 tile rows for any level.
HEVC_MAX_TILE_ROWS    = 22
# // A.4.1: table A.6 allows at most 20 tile columns for any level.
HEVC_MAX_TILE_COLUMNS = 20

# // A.4.2: table A.6 allows at most 600 slice segments for any level.
HEVC_MAX_SLICE_SEGMENTS = 600

# // 7.4.7.1: in the worst case (tiles_enabled_flag and
# // entropy_coding_sync_enabled_flag are both set), entry points can be
# // placed at the beginning of every Ctb row in every tile, giving an
# // upper bound of (num_tile_columns_minus1 + 1) * PicHeightInCtbsY - 1.
# // Only a stream with very high resolution and perverse parameters could
# // get near that, though, so set a lower limit here with the maximum
# // possible value for 4K video (at most 135 16x16 Ctb rows).
HEVC_MAX_ENTRY_POINT_OFFSETS = HEVC_MAX_TILE_COLUMNS * 135

# // A.3.7: Screen content coding extensions
HEVC_MAX_PALETTE_PREDICTOR_SIZE = 128

def IS_IDR(s): return s.nal_unit_type == HEVC_NAL_IDR_W_RADL or s.nal_unit_type == HEVC_NAL_IDR_N_LP
def IS_BLA(s): return s.nal_unit_type == HEVC_NAL_BLA_W_RADL or s.nal_unit_type == HEVC_NAL_BLA_W_LP or s.nal_unit_type == HEVC_NAL_BLA_N_LP
def IS_IRAP(s): return s.nal_unit_type == HEVC_NAL_BLA_W_LP or s.nal_unit_type <= HEVC_NAL_RSV_IRAP_VCL23
def IS_SLICE(s): return (s.nal_unit_type in [HEVC_NAL_TRAIL_R, HEVC_NAL_TRAIL_N, HEVC_NAL_TSA_N,HEVC_NAL_TSA_R, HEVC_NAL_STSA_N, HEVC_NAL_STSA_R, HEVC_NAL_BLA_W_LP, HEVC_NAL_BLA_W_RADL, HEVC_NAL_BLA_N_LP, HEVC_NAL_IDR_W_RADL, HEVC_NAL_IDR_N_LP, HEVC_NAL_CRA_NUT, HEVC_NAL_RADL_N, HEVC_NAL_RADL_R, HEVC_NAL_RASL_N, HEVC_NAL_RASL_R])
def IS_INTRA(s): return IS_IDR(s) or (IS_SLICE(s) and s.slice_type == HEVC_SLICE_I)
def IS_IDR2(s): return IS_IDR(s) or s.nal_unit_type == HEVC_NAL_CRA_NUT

HEVC_REF_ST = 0
HEVC_REF_LT = 1

HEVC_CHROMA_IDC_400 = 0
HEVC_CHROMA_IDC_420 = 1
HEVC_CHROMA_IDC_422 = 2
HEVC_CHROMA_IDC_444 = 3

ST_CURR_BEF = 0
ST_CURR_AFT = 1
ST_FOLL = 2
LT_CURR = 3
LT_FOLL = 4
NB_RPS_TYPE = 5

HEVC_FRAME_FLAG_OUTPUT    = (1 << 0)
HEVC_FRAME_FLAG_SHORT_REF = (1 << 1)
HEVC_FRAME_FLAG_LONG_REF  = (1 << 2)
HEVC_FRAME_FLAG_BUMPING   = (1 << 3)
