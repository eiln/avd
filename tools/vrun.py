#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from avid.vp9.decoder import AVDVP9Decoder

dec = AVDVP9Decoder()
units = dec.parse("../test/matrix-128x64-30.ivf")
for x in units:
	print(x)
	dec.generate(x)
