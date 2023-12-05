#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

H264_NAL_SLICE_NONIDR    = 1
H264_NAL_SLICE_PART_A    = 2
H264_NAL_SLICE_PART_B    = 3	# /* I, SI residual blocks */
H264_NAL_SLICE_PART_C    = 4	# /* P, B residual blocks */
H264_NAL_SLICE_IDR       = 5
H264_NAL_SEI             = 6
H264_NAL_SPS             = 7
H264_NAL_PPS             = 8
H264_NAL_ACC_UNIT_DELIM  = 9
H264_NAL_END_SEQ         = 10
H264_NAL_END_STREAM      = 11
H264_NAL_FILLER_DATA     = 12
H264_NAL_SPS_EXT         = 13
H264_NAL_PREFIX_NAL_UNIT = 14	# /* SVC/MVC */
H264_NAL_SUBSET_SPS      = 15	# /* SVC/MVC */
H264_NAL_SLICE_AUX       = 19
H264_NAL_SLICE_EXT       = 20	# /* SVC/MVC */

H264_PRIMARY_PIC_TYPE_I           = 0
H264_PRIMARY_PIC_TYPE_P_I         = 1
H264_PRIMARY_PIC_TYPE_P_B_I       = 2
H264_PRIMARY_PIC_TYPE_SI          = 3
H264_PRIMARY_PIC_TYPE_SP_SI       = 4
H264_PRIMARY_PIC_TYPE_I_SI        = 5
H264_PRIMARY_PIC_TYPE_P_I_SP_SI   = 6
H264_PRIMARY_PIC_TYPE_P_B_I_SP_SI = 7

H264_REF_PIC_MOD_PIC_NUM_SUB  = 0
H264_REF_PIC_MOD_PIC_NUM_ADD  = 1
H264_REF_PIC_MOD_LONG_TERM    = 2
H264_REF_PIC_MOD_END          = 3
# /* MVC */
H264_REF_PIC_MOD_VIEW_IDX_SUB = 4
H264_REF_PIC_MOD_VIEW_IDX_ADD = 5

H264_MMCO_END              = 0
H264_MMCO_SHORT2UNUSED     = 1
H264_MMCO_FORGET_LONG      = 2
H264_MMCO_SHORT_TO_LONG    = 3
H264_MMCO_FORGET_LONG_MANY = 4
H264_MMCO_FORGET_ALL       = 5
H264_MMCO_THIS_TO_LONG     = 6

H264_SLICE_TYPE_P  = 0
H264_SLICE_TYPE_B  = 1
H264_SLICE_TYPE_I  = 2
H264_SLICE_TYPE_SP = 3
H264_SLICE_TYPE_SI = 4

H264_FIELD_FRAME  = 0
H264_FIELD_TOP    = 1
H264_FIELD_BOTTOM = 2

H264_MAX_SPS_COUNT  = 32
H264_MAX_PPS_COUNT  = 256
H264_MAX_DPB_FRAMES = 16
H264_MAX_REFS       = 2 * H264_MAX_DPB_FRAMES
H264_MAX_RPLM_COUNT = H264_MAX_REFS + 1
H264_MAX_MMCO_COUNT = H264_MAX_REFS * 2 + 3

H264_CHROMA_IDC_400 = 0
H264_CHROMA_IDC_420 = 1
H264_CHROMA_IDC_422 = 2
H264_CHROMA_IDC_444 = 3

# H.264 table A-1.
h264_levels = [
    #  Name          MaxMBPS                   MaxBR              MinCR
    #  | level_idc     |       MaxFS            |    MaxCPB        | MaxMvsPer2Mb
    #  |     | cs3f    |         |  MaxDpbMbs   |       |  MaxVmvR |   |
    [ "1",   10, 0,     1485,     99,    396,     64,    175,   64, 2,  0 ],
    [ "1b",  11, 1,     1485,     99,    396,    128,    350,   64, 2,  0 ],
    [ "1b",   9, 0,     1485,     99,    396,    128,    350,   64, 2,  0 ],
    [ "1.1", 11, 0,     3000,    396,    900,    192,    500,  128, 2,  0 ],
    [ "1.2", 12, 0,     6000,    396,   2376,    384,   1000,  128, 2,  0 ],
    [ "1.3", 13, 0,    11880,    396,   2376,    768,   2000,  128, 2,  0 ],
    [ "2",   20, 0,    11880,    396,   2376,   2000,   2000,  128, 2,  0 ],
    [ "2.1", 21, 0,    19800,    792,   4752,   4000,   4000,  256, 2,  0 ],
    [ "2.2", 22, 0,    20250,   1620,   8100,   4000,   4000,  256, 2,  0 ],
    [ "3",   30, 0,    40500,   1620,   8100,  10000,  10000,  256, 2, 32 ],
    [ "3.1", 31, 0,   108000,   3600,  18000,  14000,  14000,  512, 4, 16 ],
    [ "3.2", 32, 0,   216000,   5120,  20480,  20000,  20000,  512, 4, 16 ],
    [ "4",   40, 0,   245760,   8192,  32768,  20000,  25000,  512, 4, 16 ],
    [ "4.1", 41, 0,   245760,   8192,  32768,  50000,  62500,  512, 2, 16 ],
    [ "4.2", 42, 0,   522240,   8704,  34816,  50000,  62500,  512, 2, 16 ],
    [ "5",   50, 0,   589824,  22080, 110400, 135000, 135000,  512, 2, 16 ],
    [ "5.1", 51, 0,   983040,  36864, 184320, 240000, 240000,  512, 2, 16 ],
    [ "5.2", 52, 0,  2073600,  36864, 184320, 240000, 240000,  512, 2, 16 ],
    [ "6",   60, 0,  4177920, 139264, 696320, 240000, 240000, 8192, 2, 16 ],
    [ "6.1", 61, 0,  8355840, 139264, 696320, 480000, 480000, 8192, 2, 16 ],
    [ "6.2", 62, 0, 16711680, 139264, 696320, 800000, 800000, 8192, 2, 16 ],
]

H264_FRAME_FLAG_OUTPUT    = (1 << 0)
H264_FRAME_FLAG_SHORT_REF = (1 << 1)
H264_FRAME_FLAG_LONG_REF  = (1 << 2)
H264_FRAME_FLAG_UNUSED    = (1 << 3)

def IS_SLICE(s): return s.nal_unit_type in [H264_NAL_SLICE_NONIDR, H264_NAL_SLICE_PART_A, H264_NAL_SLICE_PART_B, H264_NAL_SLICE_PART_C, H264_NAL_SLICE_IDR, H264_NAL_SLICE_AUX, H264_NAL_SLICE_EXT]
