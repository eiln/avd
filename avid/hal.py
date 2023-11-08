#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from collections import namedtuple
from .utils import *

class AVDInst(namedtuple('AVDInst', ['val', 'name', 'pos', 'idx'])):
    def __repr__(self):
        if  self.name.startswith("hdr"):
            n = ANSI_PURPLE
        elif self.name.startswith("slc"):
            n = ANSI_CYAN
        elif self.name.startswith("fw"):
            n = ANSI_YELLOW
        else:
            n = ANSI_WHITE
        c = "\033[1;%dm" % n
        disp_name = c + self.name + "\033[0m"
        if isinstance(self.idx, int):
            disp_name += f"{c}[\033[0m{self.idx}{c}]\033[0m"
        disp_val = f"{hex(self.val).rjust(2+8)}"
        disp_idx = f"[{hl(str(self.pos).rjust(2), ANSI_GREEN)}]"
        return f'{disp_idx} {disp_val} | {disp_name}'

class AVDHal:
    def __init__(self, ctx=None):
        self.ctx = ctx
        self.inst_stream = []
        self.stfu = False
        self.fp = {}

    def log(self, x):
        if (not self.stfu):
            print(f"[AVD] {x}")

    def setup(self, ctx):
        self.ctx = ctx
        self.inst_stream = []

    def avd_set(self, val, name="", idx=None):
        if not name:
            name = f"unk_{str(len(self.inst_stream))}"
        inst = AVDInst(val, name, len(self.inst_stream), idx)
        self.log(inst)
        assert(val >= 0)
        self.inst_stream.append(val)
        if isinstance(idx, int):
            self.fp[name][idx] = val
        else:
            self.fp[name] = val
