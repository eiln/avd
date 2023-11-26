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
    last = 0
    addrs = [0x0]
    out = []
    for i,path in enumerate(paths):
        #if (i < 2): continue
        if (args.verbose):
            print(i, path)
        sl = headers[i]
        if (args.verbose):
            print(sl)
        params = open(path, "rb").read()
        fp = fpcls.parse(params)
        if (args.verbose):
            print(fp)
        if 1:
            x = fp.hdr.hdr_dc_pps_tile_addr_lsb8[7]
            if (x) not in addrs:
                addrs.append(x)
            y = addrs.index(x)
        if 1:
            x = fp.slc.slc_bd4_sps_tile_addr2_lsb8
            if (x) not in addrs:
                addrs.append(x)
            z = addrs.index(x)
        #k = getattr(sl, "pic_order_cnt", 0)
        #h = getattr(sl, "slice_temporal_mvp_enabled_flag", 0)
        out.append((i, y - 1, z - 1, sl.slice_type))
        #last = k

    out = np.array(out)
    print(out)
    if (len(addrs)):
        print(", ".join([hex(x) for x in addrs]))
    #print((out[:, 2] - 1).tolist())
