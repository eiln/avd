#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import numpy as np
import os
from copy import deepcopy
from tools.common import *
from tools.hdr import parse_headers

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='find regressions between fp & headers')
    parser.add_argument('dir', type=str, help="trace dir name")
    parser.add_argument('-m', '--mode', type=str, default="", help="codec mode")
    parser.add_argument('-i', '--input', type=str, default="", help="path to bitstream")
    parser.add_argument('-s', '--start', type=int, default=0, help="starting index")
    parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
    parser.add_argument('-a', '--all', action='store_true', help="run all")
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-c', '--decimal', action='store_true')
    parser.add_argument('-d', '--decode', action='store_true')
    args = parser.parse_args()

    if (not args.decimal):
        np.set_printoptions(formatter={'int':lambda x: "0x%06x" % (x)})
    else:
        np.set_printoptions(threshold=sys.maxsize)

    if (not args.input):
        args.input = resolve_input(args.dir)
    dirname = resolve_input(args.dir, isdir=True, mode=args.mode)
    if (not args.mode):
        args.mode = ffprobe(dirname)
    paths = os.listdir(dirname)
    paths = sorted([os.path.join(dirname, path) for path in paths if "frame" in path])
    paths = paths if args.all else paths[args.start:args.start+args.num]
    assert(len(paths))

    fpcls = get_fpcls(paths[0])
    if (args.decode):
        decls = get_decoder(args.mode)
        dec = decls()
        dec.stfu = True
        dec.hal.stfu = True
        slices = dec.setup(args.input, **vars(args))
    else:
        slices, _ = parse_headers(args.input, num=len(paths))

    addrs = [0x0]
    out = []
    for i,path in enumerate(paths):
        if (args.verbose):
            print(i, path)

        sl = slices[i]
        if (args.verbose):
            print(sl)
        if (args.decode):
            dec.ctx.active_sl = sl
            dec.init_slice()
            ctx = deepcopy(dec.ctx)

        params = open(path, "rb").read()
        fp = fpcls.parse(params)
        if (args.verbose):
            print(fp)

        if 1:
            x = fp.hdr.hdr_bc_sps_tile_addr_lsb8
            if (x) not in addrs:
                addrs.append(x)
            y = addrs.index(x) - 1
        if 1:
            x = fp.slc.slc_a78_sps_tile_addr2_lsb8
            if (x) not in addrs:
                addrs.append(x)
            z = addrs.index(x) - 1

        z1 = sl.pic.idx
        z2 = 0
        if (sl.slice_type == 1):
            z2 = sl.list1[0].idx
        out.append((i, y, z1, z, z2, sl.slice_type))
        dec.finish_slice()

    out = np.array(out)
    print(out)
    if (len(addrs)):
        print(", ".join([hex(x) for x in addrs]))
    #print((out[:, 2] - 1).tolist())
