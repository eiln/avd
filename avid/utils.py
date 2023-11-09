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

def clog2(x):
	if (x <= 0):
		raise ValueError("domain error")
	return (x - 1).bit_length() # python is incredible

def flog2(x):
	if x <= 0:
		raise ValueError("domain error")
	return x.bit_length() - 1

ANSI_RED    = 31
ANSI_GREEN  = 32
ANSI_YELLOW = 33
ANSI_BLUE   = 34
ANSI_PURPLE = 35
ANSI_CYAN   = 36
ANSI_WHITE  = 37

def hl(x, n):
    if (n == None): return x
    return f"\033[1;{n}m{str(x)}\033[0m"

class dotdict(dict):
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    def __getattr__(self, key):
        try:
            return self.__getitem__(key)
        except KeyError as ex:
            raise AttributeError(key)
