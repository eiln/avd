#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from construct import *
from .constructutils import *
import numpy as np

class ProbsConstructClass(ConstructClass):
	def __init__(self):
		super().__init__()

	def _post_parse(self, obj):
		for key in list(obj):
			if (key.startswith("_") or "pad" in key): continue
			obj[key] = np.array(obj[key])
		return obj
