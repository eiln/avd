#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from construct import *
from construct.lib import *
from .constructutils import *

u8 = Hex(Int8ul)
u16 = Hex(Int16ul)
u32 = Hex(Int32ul)
u64 = Hex(Int64ul)

class AvdV3PiodmaHeader(ConstructClass):
	subcon = Struct(
		"pio_piodma1_word" / u32,
		"pio_4_codec" / ExprValidator(u32, obj_ >= 0 and obj_ <= 4), # 32 fucking bits for max 4 codes it doesn't need, this will be a recurring theme
		"pio_8_notused" / u32,
		"pio_c_notused" / u32,
		"pio_10_notused" / u32,
		"pio_14_deadcafe_notused" / ExprValidator(u32, obj_ == 0xdeadcafe),
		"pio_18_101_notused" / ExprValidator(u32, obj_ == 0x10101),
		"pio_1c_slice_count" / u32,
		"pio_20_piodma3_offset" / u32, #ExprValidator(u32, obj_ == 0x8b4c0)
		"pio_24_pad" / ZPadding(0x4),
	)
	def __init__(self):
		super().__init__()

class AVDFakeFrameParams(dict):
    # fake dict to diff with parsed frame_params
    def __init__(self):
        super().__init__()
        self.keynames = ["hdr", "slc", "inp"]

    @classmethod
    def new(cls):
        obj = cls()
        return obj

    def __repr__(self):
        parts = []
        keys = [k for k in list(self.keys()) if any(k.startswith(x) for x in list(self.keynames))]
        keys = sorted(keys, key=lambda x: int(x.split("_")[1], 16))
        last = ""
        for k in keys:
            if isinstance(k, str) and k.startswith("_"): continue

            hdr = f"\t\033[0;34m{k.ljust(32)}\033[0m = "
            s = hdr
            if not last:
                last = k[:3]
                s = "\n" + f"  {k[:3]}:\n" + hdr
            elif last != k[:3]:
                last = k[:3]
                s = "\n" + f"  {k[:3]}:\n" + hdr

            v = self[k]
            if isinstance(v, stringtypes):
                s += reprstring(v)
            elif isinstance(v, int):
                s += hex(v)
            elif isinstance(v, ListContainer) or isinstance(v, list):
                tmp = []
                stride = 4
                for n in range(len(v) // stride):
                    y = v[n*stride:(n+1)*stride]
                    if (not sum(y)):
                        t = "-"
                        continue
                    else:
                        if ("lsb" in k):
                            t = ", ".join(["0x%05x" % x for x in y])
                        else:
                            t = ", ".join([hex(x) for x in y])
                    if (n != 0):
                        t = "\t".ljust(len(hdr)) + t
                    tmp.append(t)
                s += "\n".join(tmp)
            else:
                s += str(v)
            parts.append(s)
        return "\n".join(parts)
