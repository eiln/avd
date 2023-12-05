#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import os
import struct
from pathlib import Path

from avid.utils import *

def nthhex(x, n): return (x & (0xf << (1 << n))) >> n * 4

def hexdump(s, sep=" "): return sep.join(["%02x"%x for x in s])
def hexdump32(s, sep=" "): return sep.join(["%08x"%x for x in struct.unpack("<%dI" % (len(s)//4), s)])
def _ascii(s): return "".join(["." if (c < 0x20 or c > 0x7e) else chr(c) for c in s])

def xxd(s, st=0, abbreviate=True, stride=16, group=2, indent="", print_fn=print):
    last = None
    skip = False
    for i in range(0,len(s),stride):
        val = s[i:i+stride]
        if val == last and abbreviate:
            if not skip:
                print_fn(indent+"%08x: *" % (i + st))
                skip = True
        else:
            print_fn(indent+"%08x: %s | %s" % (
                i + st,
                " ".join(hexdump(val[i:i+group], sep='').ljust(4)
                          for i in range(0, stride, group)),
                _ascii(val).ljust(stride)))
            last = val
            skip = False

def xxde(s, st=0, group=16, abbreviate=True, do_ascii=True, print_fn=print):
	last = None
	skip = False
	for i in range(0,len(s),group):
		val = s[i:i+group]
		if val == last and abbreviate:
			if not skip:
				print_fn("%08x: *" % (i + st))
				skip = True
		else:
			width = (8 + 1) + (8 + 1)*(group // 4)
			line = "%08x: %s" % (i + st, hexdump32(val, sep=" "))
			line = line.ljust(width)
			if (do_ascii): line += " | %s" % (_ascii(val))
			print_fn(line)
			last = val
			skip = False

def chexdiff32(prev, cur, ascii=True, offset=0, offset2=None):
    assert len(cur) % 4 == 0
    count = len(cur) // 4
    words = struct.unpack("<%dI" % count, cur)

    if prev is None:
        last = None
    else:
        assert len(prev) == len(cur)
        last = struct.unpack("<%dI" % count, prev)

    row = 8
    skipping = False
    out = []
    for i in range(0, count, row):
        off_text = f"{offset + i * 4:016x}"
        if offset2 is not None:
            off_text += f"/{offset2 + i * 4:08x}"
        if not last:
            if i != 0 and words[i:i+row] == words[i-row:i]:
                if not skipping:
                    out.append(f"{off_text} *\n")
                skipping = True
            else:
                out.append(f"{off_text} ")
                for new in words[i:i+row]:
                    out.append("%08x " % new)
                if ascii:
                    out.append("| " + _ascii(cur[4*i:4*(i+row)]))
                out.append("\n")
                skipping = False
        elif last[i:i+row] != words[i:i+row]:
            out.append(f"{off_text} ")
            for old, new in zip(last[i:i+row], words[i:i+row]):
                so = "%08x" % old
                sn = s = "%08x" % new
                if old != new:
                    s = "\x1b[32m"
                    ld = False
                    for a,b in zip(so, sn):
                        d = a != b
                        if ld != d:
                            s += "\x1b[31;1;4m" if d else "\x1b[32m"
                            ld = d
                        s += b
                    s += "\x1b[m"
                out.append(s + " ")
            if ascii:
                out.append("| " + _ascii(cur[4*i:4*(i+row)]))
            out.append("\n")
    return "".join(out)

def bitrepr(size, bits):
	out = []
	for i in range(size-1, -1, -1):
		for j in range(7, -1, -1):
			byte = (bits[i] >> j) & 1
			out.append(byte)
	return ''.join(['%u' % x for x in out])

def bitrepr32(x): return bitrepr(4, struct.pack("<I", x))

def bitrepr_diff(x, y):
	out = []
	for i in range(32):
		if (x[i] == y[i]):
			out.append(hl(x[i], None))
		else:
			out.append(hl(x[i], ANSI_RED))
	return "".join(out)

def bassert(x, y, msg="", nonfatal=False):
    if (x != y):
        if (msg):
            print(hl(f"[ASSERT] {msg}", ANSI_RED))
        diff = chexdiff32(x, y)
        print(diff)
    if (not nonfatal):
        assert(x == y)

def getext(mode):
    if (mode in ["vp9", "vp09", "av1", "av01"]): return [".ivf"]
    if (mode in ["h264", "avc"]): return [".h264", ".264"]
    if (mode in ["h265", "hevc"]): return [".h265", ".265"]

def mode2fourcc(mode):
    if (mode in ["h264", "avc"]): return "h264"
    if (mode in ["h265", "hevc"]): return "h265"
    if (mode in ["vp9", "vp09"]): return "vp09"
    if (mode in ["av1", "av01"]): return "av01"

def ffprobe(path):
    fname, ext = os.path.splitext(path)
    if (not ext): # dir
        mode = os.path.split(os.path.split(path)[0])[1]
        return mode2fourcc(mode)
    if ext in [".h264", ".264"]: return "h264"
    if ext in [".h265", ".265"]: return "h265"
    if ext in [".ivf"]:
        from avid.vp9.parser import IVFDemuxer
        dmx = IVFDemuxer()
        return dmx.read_mode(path)
    raise ValueError("unsupported format (%s)" % (ext))

def resolve_datadir(path):
    if (not Path(path).exists()):
        return (Path(__file__).parent / ('../data/%s' % (path))).resolve()
    return path

def resolve_input(path, isdir=False):
    path = resolve_datadir(path)
    if (isdir): return path
    if (not Path(path).exists()) or (os.path.isdir(path)):
        mode = os.path.split(os.path.split(path)[0])[1]
        for ext in getext(mode):
            p = path.as_posix() + ext
            if (os.path.exists(p)): return p
    return path

def get_fpcls(path):
    # determine mode
    _, mode = struct.unpack("<II", open(path, "rb").read()[:8])
    if   (mode == 0):
        from avid.h265.fp import AVDH265V3FrameParams
        fpcls = AVDH265V3FrameParams
    elif (mode == 1):
        from avid.h264.fp import AVDH264V3FrameParams
        fpcls = AVDH264V3FrameParams
    elif (mode == 2):
        from avid.vp9.fp import AVDVP9V3FrameParams
        fpcls = AVDVP9V3FrameParams
    else:
        raise ValueError("Not supported")
    return fpcls
