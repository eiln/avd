#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
#
# Copyright (c) 2023 Eileen Yoon <eyn@gmx.com>
#
# Apple Video Decoder Cortex M-3 coprocessor firmware emulator
#
# To solve the problem of feeding the hardware an arbitrarily-long stream of
# instructions, the engineers decided on a "FIFO" circuitry that, when written
# a u32, either 1) caches it into its hidden internal state (for header words)
# or 2) executes it (for command words).
#
# Unlucky us, as all the words are jammed in-place into a single memory location
# and into the void (either way), one cannot trace the instruction contents or
# their order via a simple before vs. after snapshot. So comes the emulator...

from unicorn import *
from unicorn.arm_const import *

import argparse
import struct
import os

AVD_CM3_CMD_SIZE     = 0x60
AVD_CM3_CMD_INIT     = 0x0
AVD_CM3_CMD_DECODE   = 0x1
AVD_CM3_CMD_ABORT    = 0x2

AVD_CM3_MODE_H264    = 0x1
AVD_CM3_MODE_VP9     = 0x2

AVD_CM3_SRAM_ADDR    = 0x108c000  # Physical offset
AVD_CM3_SRAM_SIZE    = 0x10000
AVD_CM3_SRAM_BASE    = 0x10000000 # CM3 alias
AVD_CM3_MMIO_BASE    = 0x3f000000
AVD_CM3_HACK_WFI_ADDRESS = 0x2b2

AVD_CM3_FIFO_COUNT   = 4   # CM3 SRAM queue
AVD_CM3_FIFO_WIDTH   = 0xe68
AVD_DART1_FIFO_COUNT = 16  # DART1/GART queue
AVD_DART1_FIFO_WIDTH = 0xb8000

def is_pow2(x): return (x != 0) and (x & (x - 1) == 0)
def round_up(x, y): return ((x + (y - 1)) & (-y))
def round_down(x, y): return (x - (x % y))

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

def bitrepr(size, bits):
	out = []
	for i in range(size-1, -1, -1):
		for j in range(7, -1, -1):
			byte = (bits[i] >> j) & 1
			out.append(byte)
	return ''.join(['%u' % x for x in out])

def bitrepr32(x): return bitrepr(4, struct.pack("<I", x))

class AVDEmulator:
	def __init__(self, firmware, trace_sram=False, format_mmio=False, verbose=False,
			trace_code=False, stfu=False, inst_only=False, show_bits=False):
		self.firmware = open(firmware, 'rb').read()
		self.trace_sram = trace_sram
		self.format_mmio = format_mmio
		self.verbose = verbose
		self.trace_code = trace_code
		self.stfu = stfu
		self.inst_only = inst_only
		self.show_bits = show_bits
		if (self.inst_only):
			self.stfu = True

		emu = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
		emu.mem_map(0x00000000, 0x10000) # IRAM / code
		emu.mem_write(0x00000000, self.firmware)
		self.emu = emu
		self.mmio_map = {}

		self.cm3ctrl_enabled_irq0 = 0
		self.cm3ctrl_enabled_irqs = [0] * 6
		self.nvic_enabled_irqs = [0] * 8
		self.piodma_iova_low = 0x00000000
		self.piodma_iova_high = 0x00000000

		self.fifo1_idx = 0
		self.dart1_space = b''
		self.cmd_idx = 0
		self.inst_stream = []
		self.hl_color = 37
		self.mode = 0

	def log(self, x, f=print):
		if (not self.stfu): return f(f'[EMU] {x}')

	def hl(self, x): return f"\033[1;{self.hl_color}m{str(x)}\033[0m"

	def set_dart1_space(self, frame_params, base_piodma_word):
		# Infer packet's DART1 FIFO index
		word = struct.unpack("<I", frame_params[:4])[0]
		assert(not((word - base_piodma_word) % AVD_CM3_FIFO_WIDTH))
		fifo1_idx = (word - base_piodma_word) // AVD_CM3_FIFO_WIDTH
		assert((fifo1_idx >= 0) and (fifo1_idx <= AVD_DART1_FIFO_COUNT))
		self.fifo1_idx = fifo1_idx

		# Pad DART1 space for easy piodma indexing
		# TODO might just fix PIODMA handler to not waste memory
		fifo1_iova = 0x4000 + (AVD_DART1_FIFO_WIDTH * self.fifo1_idx)
		self.log("setting frame params @ iova 0x%x n=%d" % (fifo1_iova, fifo1_idx))
		self.dart1_space = b"\00"*fifo1_iova + frame_params
		return fifo1_idx

	def set_params_h264(self, frame_params):
		fifo1_idx = self.set_dart1_space(frame_params, 0x27def15)
		fifo1_iova = 0x4000 + (AVD_DART1_FIFO_WIDTH * fifo1_idx)

		"""
		00000000: 00000401 00000000 00004000 00000001 00010003 00000001 00000000 0108ef38
		00000020: 00004284 0108ef44 00004468 000046e0 0008f4c0 00000000 0108ef6c 0108f130
		00000040: 0108f18c 0000464c 000046c8 00000000 00000000 00000000 00000000 00000000
		"""
		cmd = [0x0] * (AVD_CM3_CMD_SIZE // 4)
		cmd[ 0] = 0x400 | AVD_CM3_CMD_DECODE
		cmd[ 1] = ((fifo1_idx % AVD_DART1_FIFO_COUNT) << 16) | fifo1_idx
		cmd[ 2] = fifo1_iova
		cmd[ 3] = fifo1_idx + 1
		cmd[ 4] = 0x10003
		cmd[ 5] = 0x1
		cmd[ 6] = 0x0
		cmd[ 7] = 0x108ef38 + (AVD_CM3_FIFO_WIDTH * (fifo1_idx % AVD_CM3_FIFO_COUNT))
		cmd[ 8] = fifo1_iova + 0x284
		cmd[ 9] = 0x108ef44 + (AVD_CM3_FIFO_WIDTH * (fifo1_idx % AVD_CM3_FIFO_COUNT))
		cmd[10] = fifo1_iova + 0x468
		cmd[11] = fifo1_iova + 0x6e0
		cmd[12] = fifo1_iova + 0x8b4c0
		cmd[13] = 0x0
		cmd[14] = 0x108ef6c + (AVD_CM3_FIFO_WIDTH * (fifo1_idx % AVD_CM3_FIFO_COUNT))
		cmd[15] = 0x108ff98 + (AVD_CM3_FIFO_WIDTH * (fifo1_idx % AVD_CM3_FIFO_COUNT))
		cmd[16] = 0x108fff4 + (AVD_CM3_FIFO_WIDTH * (fifo1_idx % AVD_CM3_FIFO_COUNT))
		cmd[17] = fifo1_iova + 0x64c
		cmd[18] = fifo1_iova + 0x6c8
		return struct.pack("<" + "I"*(len(cmd)), *cmd)

	def set_params_vp9(self, frame_params):
		fifo1_idx = self.set_dart1_space(frame_params, 0x209ef15)
		fifo1_iova = 0x4000 + (AVD_DART1_FIFO_WIDTH * fifo1_idx)

		"""
		00000000: 00000801 00000000 00004000 000002c1 00000003 0108ef38 0108ef40 00000001
		00000020: 00004aa4 0108efb8 0108f088 0108f118 000042a4 00004210 0000428c 00000000
		00000040: 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
		"""
		cmd = [0x0] * (AVD_CM3_CMD_SIZE // 4)
		cmd[ 0] = 0x800 | AVD_CM3_CMD_DECODE
		cmd[ 1] = ((fifo1_idx % AVD_DART1_FIFO_COUNT) << 16) | fifo1_idx
		cmd[ 2] = fifo1_iova
		cmd[ 3] = fifo1_idx
		cmd[ 4] = 0x3
		cmd[ 5] = 0x108ef38 + (AVD_CM3_FIFO_WIDTH * (fifo1_idx % AVD_CM3_FIFO_COUNT))
		cmd[ 6] = 0x108ef40 + (AVD_CM3_FIFO_WIDTH * (fifo1_idx % AVD_CM3_FIFO_COUNT))
		cmd[ 7] = 0x1
		cmd[ 8] = fifo1_iova + 0xaa4
		cmd[ 9] = 0x108efb8 + (AVD_CM3_FIFO_WIDTH * (fifo1_idx % AVD_CM3_FIFO_COUNT))
		cmd[10] = 0x108f088 + (AVD_CM3_FIFO_WIDTH * (fifo1_idx % AVD_CM3_FIFO_COUNT))
		cmd[11] = 0x108f118 + (AVD_CM3_FIFO_WIDTH * (fifo1_idx % AVD_CM3_FIFO_COUNT))
		cmd[12] = fifo1_iova + 0x2a4
		cmd[13] = fifo1_iova + 0x210
		cmd[14] = fifo1_iova + 0x28c
		cmd[15] = 0x0
		cmd[16] = 0x0
		cmd[17] = 0x0
		cmd[18] = 0x0
		return struct.pack("<" + "I"*(len(cmd)), *cmd)

	def set_params(self, frame_path):
		self.log("reading frame params from %s" % (frame_path))
		frame_params = open(frame_path, "rb").read()
		xxde(frame_params[:0x40], print_fn=self.log)
		header = struct.unpack("<%dI" % (0x10), frame_params[:0x40])
		assert(header[5] == 0xdeadcafe) # sanity check

		if   (header[1] == AVD_CM3_MODE_H264):
			self.mode = AVD_CM3_MODE_H264
			self.hl_color = 34  # blue
			self.log(f"Mode: {self.hl('H264')}")
			return self.set_params_h264(frame_params)
		elif (header[1] == AVD_CM3_MODE_VP9):
			self.mode = AVD_CM3_MODE_VP9
			self.hl_color = 32  # green
			self.log(f"Mode: {self.hl('VP9')}")
			return self.set_params_vp9(frame_params)

		raise ValueError("unsupported codec (%d) or corrupted packet" % (header[1]))

	def get_cmd_addr(self, cmd_idx): return 0x108eb30 + (cmd_idx * AVD_CM3_CMD_SIZE)

	def start(self):
		self.map_mmio()
		self.set_mmio_map()
		self.set_mmio_defaults()
		initial_sp = struct.unpack("<I", self.firmware[0:4])[0]
		initial_pc = struct.unpack("<I", self.firmware[4:8])[0]
		self.log(f"starting @ {initial_pc:08x} with SP {initial_sp:08x}")
		self.emu.reg_write(UC_ARM_REG_SP, initial_sp)
		self.emu.emu_start(initial_pc, 0)
		self.dump_regs()
		self.dump_firmware_logs()

	def trigger_irq(self, irq_handler):
		emu = self.emu
		self.log(f"triggering IRQ @ {irq_handler:08x}")
		emu.reg_write(UC_ARM_REG_LR, AVD_CM3_HACK_WFI_ADDRESS + 1)
		emu.reg_write(UC_ARM_REG_PC, irq_handler)
		emu.emu_start(irq_handler, 0)

	def dump_regs(self):
		emu = self.emu
		r0 = emu.reg_read(UC_ARM_REG_R0)
		r1 = emu.reg_read(UC_ARM_REG_R1)
		r2 = emu.reg_read(UC_ARM_REG_R2)
		r3 = emu.reg_read(UC_ARM_REG_R3)
		self.log(f"R0  = {r0:08X}\tR1  = {r1:08X}\tR2  = {r2:08X}\tR3  = {r3:08X}")
		r4 = emu.reg_read(UC_ARM_REG_R4)
		r5 = emu.reg_read(UC_ARM_REG_R5)
		r6 = emu.reg_read(UC_ARM_REG_R6)
		r7 = emu.reg_read(UC_ARM_REG_R7)
		self.log(f"R4  = {r4:08X}\tR5  = {r5:08X}\tR6  = {r6:08X}\tR7  = {r7:08X}")
		r8 = emu.reg_read(UC_ARM_REG_R8)
		r9 = emu.reg_read(UC_ARM_REG_R9)
		r10 = emu.reg_read(UC_ARM_REG_R10)
		r11 = emu.reg_read(UC_ARM_REG_R11)
		self.log(f"R8  = {r8:08X}\tR9  = {r9:08X}\tR10 = {r10:08X}\tR11 = {r11:08X}")
		r12 = emu.reg_read(UC_ARM_REG_R12)
		sp = emu.reg_read(UC_ARM_REG_SP)
		lr = emu.reg_read(UC_ARM_REG_LR)
		pc = emu.reg_read(UC_ARM_REG_PC)
		self.log(f"R12 = {r12:08X}\tSP  = {sp:08X}\tLR  = {lr:08X}\tPC  = {pc:08X}")

	def dump_firmware_logs(self):
		logs = self.avd_read(0x108c000, 0x400)
		xxde(logs, print_fn=self.log, do_ascii=True)

	def dump_sram(self, fname="sram.bin"):
		open(fname, "wb").write(self.emu.mem_read(AVD_CM3_SRAM_BASE, AVD_CM3_SRAM_SIZE))

	def hook_code(self, emu, addr, size, data):
		if (self.trace_code):
			instruction = emu.mem_read(addr, size)
			instruction_str = ''.join('{:02x} '.format(x) for x in instruction)
			pc = emu.reg_read(UC_ARM_REG_PC)
			self.log('PC: %04x INST: %s' % (pc, instruction_str))
			self.dump_regs()
 
	def hook_mmio(self, emu, access, addr, size, val, data):
		if addr in self.mmio_map:
			if access == UC_MEM_READ:
				read_fn = self.mmio_map[addr][0]
				out_val = read_fn(addr)
				if out_val is not None:
					emu.mem_write(addr, struct.pack("<I", out_val))
			elif access == UC_MEM_WRITE:
				write_fn = self.mmio_map[addr][1]
				write_fn(addr, val)
			return

		pc = emu.reg_read(UC_ARM_REG_PC)
		if access == UC_MEM_READ:
			if (self.format_mmio):
				print("avd_r%d(0x%x)" % (size*8, self.from_avdaddr(addr)))
			else:
				self.log("%04x: %s: R%d @ %08x" % (pc, self.hl("MMIO"), size*8, addr))
		elif access == UC_MEM_WRITE:
			if (self.format_mmio):
				print("avd_w%d(0x%x, 0x%x)" % (size*8, self.from_avdaddr(addr), val))
			else:
				self.log("%04x: %s: W%d @ %08x val 0x%x" % (pc, self.hl("MMIO"), size*8, addr, val))

		prefix = "r" if access == UC_MEM_READ else "w"
		name = "%s_%x" % (prefix, addr)
		f = getattr(self, name, None)
		if callable(f):
			if (access == UC_MEM_READ):
				emu.mem_write(addr, struct.pack("<I", f(addr)))
			elif (access == UC_MEM_WRITE):
				f(addr, val)
			return

	def hook_sram(self, emu, access, addr, size, val, data):
		pc = emu.reg_read(UC_ARM_REG_PC)
		if (access == UC_MEM_READ):
			self.log(f"{pc:04x}: SRAM: R{str(size*8).ljust(2)} @ {addr:08x}")
		else:
			self.log(f"{pc:04x}: SRAM: W{str(size*8).ljust(2)} @ {addr:08x} val 0x{val:x}")
		if (self.verbose): self.dump_regs()

	def map_mmio(self):
		emu = self.emu
		emu.mem_map(AVD_CM3_SRAM_BASE, AVD_CM3_SRAM_SIZE)
		if (self.trace_sram):
			emu.hook_add(UC_HOOK_MEM_READ, self.hook_sram, begin=AVD_CM3_SRAM_BASE, end=AVD_CM3_SRAM_BASE + AVD_CM3_SRAM_SIZE)
			emu.hook_add(UC_HOOK_MEM_WRITE, self.hook_sram, begin=AVD_CM3_SRAM_BASE, end=AVD_CM3_SRAM_BASE + AVD_CM3_SRAM_SIZE)

		MMIO_BLOCKS = [
			(0x40070000, 0x4000),  # PIODMA
			(0x40100000, 0x10000), # Decode/DMA
			(0x40400000, 0x4000),  # Wrap
			(0x50010000, 0x4000),  # Peripheral Bus/Mailbox
			(0xe000c000, 0x4000),  # SCS
		]
		for (addr, size) in MMIO_BLOCKS:
			emu.mem_map(addr, size)
			emu.hook_add(UC_HOOK_MEM_READ, self.hook_mmio, begin=addr, end=addr+size)
			emu.hook_add(UC_HOOK_MEM_WRITE, self.hook_mmio, begin=addr, end=addr+size)
		emu.hook_add(UC_HOOK_CODE, self.hook_code, begin=0x00000000, end=0xffffffff)

	def r_40070004(self, addr): # 0x40070004: PIODMA_STATUS
		return 0x1 # Fake status to be done instantly, set no other bits

	def r_4007004c(self, addr): # 0x4007004c: PIODMA_ADDR_LOW
		return self.piodma_iova_low

	def w_4007004c(self, addr, val):
		self.piodma_iova_low = val

	def r_40070050(self, addr): # 0x40070050: PIODMA_ADDR_HIGH
		return self.piodma_iova_high

	def w_40070050(self, addr, val):
		self.piodma_iova_high = val

	def w_40070054(self, addr, val): # 0x40070054: PIODMA_COMMAND
		piodma_iova = self.piodma_iova_high << 32 | self.piodma_iova_low
		# Peek ahead because we are not DMA controller
		word_size = 0x4
		word = struct.unpack("<I", self.dart1_space[piodma_iova:piodma_iova+word_size])[0]
		self.log("PIODMA: src iova: 0x%x cmd: 0x%x word: 0x%x" % (piodma_iova, val, word))

		dst_addr = word & ~0x3fd0001
		dst_addr = dst_addr & ~(dst_addr & 0x20000) | ((dst_addr & 0x20000) >> 1)
		dst_addr |= 0x1080000

		size = (val << 2) >> 8
		self.log("PIODMA: copying 0x%x bytes to 0x%x" % (size, dst_addr))
		buf = self.dart1_space[piodma_iova+word_size:piodma_iova+size]
		xxde(buf[:0x40], print_fn=self.log)
		self.avd_write(dst_addr, buf)
		if (self.verbose): self.dump_firmware_logs()

	def save_inst(self, addr, val):
		if (self.inst_only):
			s = "[EMU]   %s" % (f'{hex(val).rjust(2+8)} | [{self.hl(str(len(self.inst_stream)).rjust(2))}]')
			if (self.show_bits):
				s += f' {bitrepr32(val)}'
			print(s)
		self.inst_stream.append(val)

	def w_4010400c(self, addr, val): # 0x4010400c: H264 inst FIFO
		self.save_inst(addr, val)

	def w_40104010(self, addr, val): # 0x40104010: VP9 inst FIFO
		self.save_inst(addr, val)

	def r_40104060(self, addr): # 0x40104060: decode status
		self.status_poll_count += 1
		if (self.status_poll_count >= 5): raise ValueError("STFU")
		return self.status_val

	def w_40104060(self, addr, val):
		if (val == 0x1000):
			self.status_val = 0x2c42108
		elif (val == 0x400000):
			self.status_val = 0x2842108

	def w_e000ed08(self, addr, val): # 0xe000ed08: write_vtor
		self.log(f"VTOR = {val:08x}")

	def write_isen(self, addr, val):
		for i in range(32):
			if val & (1 << i):
				reg_idx = (addr - 0xe000e100) // 4
				irq_line = reg_idx * 32 + i
				self.log(f"NVIC enabling IRQ {irq_line}")
				self.nvic_enabled_irqs[reg_idx] |= (1 << i)

	def read_isen(self, addr):
		reg_idx = (addr - 0xe000e100) // 4
		return self.nvic_enabled_irqs[reg_idx]

	def write_cm3ctrl_irq_en_0(self, addr, val):
		old_val = self.cm3ctrl_enabled_irq0
		for i in range(14):
			if (not (old_val & (1 << i))) and (val & (1 << i)):
				self.log(f"Enabling IRQ #{i}")
			if (old_val & (1 << i)) and (not (val & (1 << i))):
				self.log(f"Disabling IRQ #{i}")
		self.cm3ctrl_enabled_irq0 = val

	def read_cm3ctrl_irq_en_0(self, addr):
		return self.cm3ctrl_enabled_irq0

	def write_cm3ctrl_irq_en(self, addr, val):
		reg_idx = (addr - 0x50010014) // 4
		old_val = self.cm3ctrl_enabled_irqs[reg_idx]
		for i in range(32):
			if (not (old_val & (1 << i))) and (val & (1 << i)):
				self.log(f"Enabling IRQ {14 + reg_idx * 32 + i}")
			if (old_val & (1 << i)) and (not (val & (1 << i))):
				self.log(f"Disabling IRQ {14 + reg_idx * 32 + i}")
		self.cm3ctrl_enabled_irqs[reg_idx] = val

	def read_cm3ctrl_irq_en(self, addr):
		reg_idx = (addr - 0x50010014) // 4
		return self.cm3ctrl_enabled_irqs[reg_idx]

	def r_50010058(self, addr): # 0x50010058: read_cm3ctrl_mbox0_retrieve
		fifo_addr = self.get_cmd_addr(self.cmd_idx)
		self.log("got cmd at 0x%x n=%d" % (fifo_addr, self.cmd_idx))
		cmd = self.avd_read(fifo_addr, AVD_CM3_CMD_SIZE)
		xxde(cmd, print_fn=self.log)
		return fifo_addr

	def set_mmio_map(self):
		self.mmio_map = {
			0x50010010: (self.read_cm3ctrl_irq_en_0, self.write_cm3ctrl_irq_en_0),
			0x50010014: (self.read_cm3ctrl_irq_en, self.write_cm3ctrl_irq_en),
			0x50010018: (self.read_cm3ctrl_irq_en, self.write_cm3ctrl_irq_en),
			0x5001001c: (self.read_cm3ctrl_irq_en, self.write_cm3ctrl_irq_en),
			0x50010020: (self.read_cm3ctrl_irq_en, self.write_cm3ctrl_irq_en),
			0x50010024: (self.read_cm3ctrl_irq_en, self.write_cm3ctrl_irq_en),
			0x50010028: (self.read_cm3ctrl_irq_en, self.write_cm3ctrl_irq_en),
			0x50010050: (lambda _addr: 0x22201, lambda _addr, _val: None), # mbox1 status
			0x5001005c: (lambda _addr: 0x20001, lambda _addr, _val: None), # mbox1 status
			0xe000e100: (self.read_isen, self.write_isen),
			0xe000e104: (self.read_isen, self.write_isen),
			0xe000e108: (self.read_isen, self.write_isen),
			0xe000e10c: (self.read_isen, self.write_isen),
			0xe000e110: (self.read_isen, self.write_isen),
			0xe000e114: (self.read_isen, self.write_isen),
			0xe000e118: (self.read_isen, self.write_isen),
			0xe000e11c: (self.read_isen, self.write_isen),
		}

	def set_mmio_defaults(self):
		avd_w32 = self.avd_w32
		avd_w32(0x1104018, 0x78) # I originally had hooks to increment these
		avd_w32(0x110401c, 0x78) # hw counters (checked on fw breakpoint)
		avd_w32(0x1104020, 0x78) # but this is the easier/lazier solution
		avd_w32(0x1104024, 0x78)
		avd_w32(0x1104028, 0x20)
		avd_w32(0x1104034, 0x0)
		avd_w32(0x110403c, 0x0)
		avd_w32(0x110405c, 0x500000)
		avd_w32(0x1104060, 0x842108)
		avd_w32(0x1104064, 0x3)
		self.status_val = 0x842108

		# DMA configure
		conf = [0x04020002, 0x00020002, 0x04020002, 0x04020002, 0x04020002, 0x00070007, 0x00070007, 0x00070007, 0x00070007, 0x00070007, 0x04020002, 0x00020002, 0x04020002, 0x04020002, 0x04020002, 0x00070007, 0x00070007, 0x00070007, 0x00070007, 0x00070007, 0x04020002, 0x02020202, 0x04020002, 0x04020002, 0x04020202, 0x00070007, 0x00070007, 0x00070007, 0x00070007, 0x00070007]
		for i,x in enumerate(conf):
			self.avd_write32(0x108ee90 + (i * 0x4), x)

	def avd_read(self, off, size): # sram
		assert((off >= AVD_CM3_SRAM_ADDR) and (off <= AVD_CM3_SRAM_ADDR + AVD_CM3_SRAM_SIZE))
		return self.emu.mem_read(AVD_CM3_SRAM_BASE | off - AVD_CM3_SRAM_ADDR, size)

	def avd_write(self, off, buf): # sram
		assert((off >= AVD_CM3_SRAM_ADDR) and (off <= AVD_CM3_SRAM_ADDR + AVD_CM3_SRAM_SIZE))
		self.emu.mem_write(AVD_CM3_SRAM_BASE | off - AVD_CM3_SRAM_ADDR, buf)

	def avd_write32(self, off, val): # sram w32
		assert((off >= AVD_CM3_SRAM_ADDR) and (off <= AVD_CM3_SRAM_ADDR + AVD_CM3_SRAM_SIZE))
		self.emu.mem_write(AVD_CM3_SRAM_BASE | off - AVD_CM3_SRAM_ADDR, struct.pack("<I", val))

	def avd_r32(self, off): # only MMIO1
		return struct.unpack("<I", self.emu.mem_read(off + AVD_CM3_MMIO_BASE, 0x4))[0]

	def avd_w32(self, off, val): # only MMIO1
		self.emu.mem_write(off + AVD_CM3_MMIO_BASE, struct.pack("<I", val))

	def from_avdaddr(self, addr):
		if (addr >> 28) == 0x4: return addr - AVD_CM3_MMIO_BASE # MMIO1
		if (addr >> 28) == 0x5: return addr - 0x4ef78004 # MMIO2
		return addr

	def doorbell_ring(self):
		self.trigger_irq(0x619d) # IRQ #4

	def avd_send_cmd(self, cmd):
		addr = self.get_cmd_addr(self.cmd_idx)
		self.avd_write(addr, cmd[:AVD_CM3_CMD_SIZE])
		self.doorbell_ring()
		opcode = struct.unpack("<I", cmd[:4])[0] & 0x1f
		self.log("Command opcode 0x%x queue n=%d success!" % (opcode, self.cmd_idx))
		self.dump_firmware_logs()
		self.cmd_idx = 0

	def avd_cm3_cmd_init(self):
		cmd = b'\00' * AVD_CM3_CMD_SIZE # AVD_CM3_CMD_INIT
		self.avd_send_cmd(cmd)

	def avd_cm3_cmd_decode(self, path):
		self.avd_cm3_cmd_init() # prep
		self.status_poll_count = 0 # reset
		self.status_val = 0x842108
		self.inst_stream = []
		cmd = self.set_params(path)
		self.avd_send_cmd(cmd)
		# avd.trigger_irq(0x6ab9) # post-decode irq ack
		# avd.trigger_irq(0x7a63) # post-decode wfi
		return self.inst_stream

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='CM3 Firmware Emulator')
	parser.add_argument('firmware', type=str, help="path to firmware")

	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument('-f', '--path', type=str, help="path to frame_params")
	group.add_argument('-d','--dir', type=str, help="frame_params trace directory")
	parser.add_argument('-p','--prefix', type=str, default="", help="directory prefix")
	parser.add_argument('-s', '--start', type=int, default=0, help="start index")
	parser.add_argument('-n', '--num', type=int, default=1, help="count from start")
	parser.add_argument('-a', '--all', action='store_true', help="emulate all in dir")

	parser.add_argument('-r', '--trace_sram', action='store_true', help="trace SRAM R/Ws")
	parser.add_argument('-c', '--trace_code', action='store_true', help="trace code")
	parser.add_argument('-m', '--format_mmio', action='store_true', help="format MMIO R/Ws")
	parser.add_argument('-v', '--verbose', action='store_true', help="verbose")
	parser.add_argument('-t', '--stfu', action='store_true')

	parser.add_argument('-u', '--inst_only', action='store_true', help="trace instruction stream only")
	parser.add_argument('-b', '--show_bits', action='store_true', help="show bits on the side for -u")
	args = parser.parse_args()

	emu = AVDEmulator(firmware=args.firmware, trace_sram=args.trace_sram, trace_code=args.trace_code, 	
			format_mmio=args.format_mmio, verbose=args.verbose, stfu=args.stfu,
			inst_only=args.inst_only, show_bits=args.show_bits)
	emu.start()

	if args.dir:
		paths = os.listdir(os.path.join(args.prefix, args.dir))
		paths = sorted([os.path.join(args.prefix, args.dir, path) for path in paths if "param" in path or "frame" in path])
		paths = paths if args.all else paths[args.start:args.start+args.num]
	else:
		paths = [args.path]

	for path in paths:
		print(path)
		inst = emu.avd_cm3_cmd_decode(path)
		# do whatever you need to do with 'inst'...
