#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import os
import numpy as np
from tools.common import *
from tools.hdr import parse_headers

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='find regressions between fp & headers')
    parser.add_argument('dir', type=str, help="trace dir name")
    parser.add_argument('-i', '--input', type=str, default="", help="path to bitstream")
    parser.add_argument('-s', '--start', type=int, default=0, help="starting index")
    parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
    parser.add_argument('-a', '--all', action='store_true', help="run all")
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-d', '--decimal', action='store_true', help="print arr in decimal")
    args = parser.parse_args()

    if (not args.decimal):
        np.set_printoptions(formatter={'int':lambda x: "0x%06x" % (x)})
    else:
        np.set_printoptions(threshold=sys.maxsize)

    if (not args.input):
        args.input = resolve_input(args.dir)
    dirname = resolve_input(args.dir, isdir=True)
    paths = os.listdir(dirname)
    paths = sorted([os.path.join(dirname, path) for path in paths if "frame" in path])
    paths = paths if args.all else paths[args.start:args.start+args.num]
    assert(len(paths))

    fpcls = get_fpcls(paths[0])
    headers, _ = parse_headers(args.input, len(paths))
    out = []
    for i,path in enumerate(paths):
        if (args.verbose):
            print(i, path)
        hdr = headers[i]
        if (args.verbose):
            print(hdr)
        params = open(path, "rb").read()
        fp = fpcls.parse(params)
        #if (args.verbose):
        #    print(fp)
        out.append((fp.slc.slc_a8c_cmd_ref_type & 0x00ffffff, hdr.slice_type))

    out = np.array(out)
    print(out)
