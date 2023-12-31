#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from construct import *
from construct.lib import *
from .constructutils import *
from math import ceil

u8 = Hex(Int8ul)
u16 = Hex(Int16ul)
u32 = Hex(Int32ul)
u64 = Hex(Int64ul)

class AVDFrameParams(ConstructClass):
    def __init__(self):
        super().__init__()

    def __str__(self, ignore=[], other=None, show_all=False) -> str:
        if (hasattr(self, "_reprkeys")):
            s = ""
            for x in self._reprkeys:
                t = str(getattr(self, x))
                if (t):
                    s += "\n" + t
            return s.strip() + "\n"

        s = "  \033[1;37m" + self.__class__.__name__ + ":\033[0m\n"
        out = []
        keys = list(self)
        keys.sort(key = lambda x: self._off.get(x, (-1, 0))[0])
        for key in keys:
            if key in ignore or key.startswith('_'):
                continue
            if "pad" in key or "zero" in key or "dfw" in key: continue

            sk = f"\t\033[0;36m{key.ljust(32)}\033[0m = "

            v = getattr(self, key)
            if isinstance(v, stringtypes):
                val_repr = reprstring(v)
                out.append(v)
            elif isinstance(v, int):
                val_repr = hex(v)
                out.append(v)
            elif (isinstance(v, ListContainer) or isinstance(v, list)):
                if (not (isinstance(v[0], int))):
                    for n in v:
                        s += "\n  " + str(n).strip() + "\n"
                    continue
                tmp = []
                stride = 4
                for n in range(ceil(len(v) / stride)):
                    y = v[n*stride:(n+1)*stride]
                    if (not (isinstance(y[0], int))):
                        print(y)
                    elif (not sum(y)):
                        t = "-"
                        continue
                    else:
                        prefix = "0x"
                        p = 0
                        if ("lsb" in key):
                            p = 5
                        if ("matrix" in key):
                            p = 8
                        if (p):
                            t = ", ".join([f"{prefix}{x:0{p}x}" for x in y])
                        else:
                            t = ", ".join([hex(x) for x in y])
                    if (n != 0):
                    	t = "\t".ljust(len("\t") + 32 + 3) + t
                    tmp.append(t)
                val_repr = "\n".join(tmp)
            else:
                s += "\n" + str(v).strip() + "\n"
                continue
            s += sk + val_repr + "\n"
        if (len(out) and sum(out) == 0): return ""
        return s + "\n"

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
