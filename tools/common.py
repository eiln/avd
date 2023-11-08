#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import struct

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

def ffprobe(path):
	import os
	fname, ext = os.path.splitext(path)
	if ext in [".h264", ".264"]:
		return "h264"
	if ext in [".h265", ".265"]:
		return "h265"
	if ext in [".ivf", "ivp9"]:
		from avid.vp9.parser import IVFDemuxer
		dmx = IVFDemuxer()
		return dmx.read_mode(path)
	raise ValueError("unsupported format (%s)" % (ext))
