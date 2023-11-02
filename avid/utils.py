#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

def round_up(x, y): return ((x + (y - 1)) & (-y))
def round_down(x, y): return (x - (x % y))

def swrap(x, w): return ((w + x) & ~w)

def ispow2(x): return (x != 0) and (x & (x - 1) == 0)
def pow2div(x): return (x & (~(x - 1)))

def nextpow2(v):
    v -= 1
    v |= v >> 1
    v |= v >> 2
    v |= v >> 4
    v |= v >> 8
    v |= v >> 16
    v += 1
    return v

def ulog2(u):
    t = (u > 0xffff) << 4; u >>= t
    s = (u > 0xff  ) << 3; u >>= s; t |= s
    s = (u > 0xf   ) << 2; u >>= s; t |= s
    s = (u > 0x3   ) << 1; u >>= s; t |= s
    return (t | (u >> 1))

def cassert(x, y, f=False):
    if (x != y):
    	print(f"\033[1;31m[ASSERT] {hex(x)} vs. {hex(y)}\033[0m")
    if not (f):
        assert(x == y)

class dotdict(dict):
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    def __getattr__(self, key):
        try:
            return self.__getitem__(key)
        except KeyError as ex:
            raise AttributeError(key)
