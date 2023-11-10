#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
from tools.ut import AVDH264UnitTest

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='Crappy unit test')
	parser.add_argument('-i', '--input', type=str, required=True, help="path to .h264")
	parser.add_argument('-d','--dir', type=str, required=True, help="matching .h264 trace dir")
	parser.add_argument('-p','--prefix', type=str, default="", help="dir prefix")
	parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
	parser.add_argument('-a', '--all', action='store_true', help="run all")
	parser.add_argument('-s', '--soft', action='store_true', help="don't assert")
	args = parser.parse_args()

	ut = AVDH264UnitTest()
	ut.test_inst(args)
