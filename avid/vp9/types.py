#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

VP9_FRAME_TYPE_KEY = 0

VP9_REFS_PER_FRAME      = 3
VP9_REF_FRAMES_LOG2     = 3
VP9_REF_FRAMES          = 8 # 1 << VP9_REF_FRAMES_LOG2
VP9_FRAME_CONTEXTS_LOG2 = 2

VP9_MAX_REF_LF_DELTAS = 4
VP9_MAX_MODE_LF_DELTAS = 2
