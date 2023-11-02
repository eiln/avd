#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright 2023 Eileen Yoon <eyn@gmx.com>

from collections import namedtuple
from .utils import dotdict

class AVDInst(namedtuple('AVDInst', ['val', 'name', 'pos', 'idx'])):
    def __repr__(self):
        if  self.name.startswith("hdr"):
            n = 35
        elif self.name.startswith("slc"):
            n = 36
        elif self.name.startswith("fw"):
            n = 33
        else:
            n = 37
        c = "\033[1;%dm" % n
        disp_name = c + self.name + "\033[0m"
        if isinstance(self.idx, int):
            disp_name += f"{c}[\033[0m{self.idx}{c}]\033[0m"
        return f' {hex(self.val).rjust(2+8)} | [{str(self.pos).rjust(2)}] {disp_name}'

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
