#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
from tools.ut import AVDVP9UnitTest

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='Crappy unit test')
	parser.add_argument('-i', '--input', type=str, required=True, help="path to .h264")
	parser.add_argument('-d','--dir', type=str, required=True, help="matching .h264 trace dir")
	parser.add_argument('-p','--prefix', type=str, default="", help="dir prefix")
	parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
	parser.add_argument('-a', '--all', action='store_true', help="run all")
	parser.add_argument('-q', '--test-probs', action='store_true')
	args = parser.parse_args()

	ut = AVDVP9UnitTest()
	if (not args.test_probs):
		ut.test_inst(args)
	else:
		ut.test_probs(args)
