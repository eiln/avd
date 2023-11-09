/*
 * Copyright 2023 Eileen Yoon <eyn@gmx.com>
 *
 * All Rights Reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice (including the next
 * paragraph) shall be included in all copies or substantial portions of the
 * Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#ifndef __IVF_H__
#define __IVF_H__

#include <assert.h>
#include <stdint.h>

typedef struct __attribute__((packed, scalar_storage_order("little-endian"))) IVFHeader {
	uint32_t signature; /* DKIF */
	uint16_t version;
	uint16_t length;
	uint8_t fourcc[4];
	uint16_t width;
	uint16_t height;
	uint32_t frame_rate_rate;
	uint32_t frame_rate_scale;
	uint32_t frame_count;
	uint8_t reserved[4];
} IVFHeader;
static_assert(sizeof(IVFHeader) == 32);

typedef struct IVFFrame {
	uint32_t size;
	uint64_t timestamp;
	const uint8_t *buf;
} IVFFrame;

typedef struct IVFContext {
	unsigned char *start;
	unsigned char *p;
	uint32_t fnum;
	IVFHeader h;
	IVFFrame f;
} IVFContext;

IVFContext *ivf_init(unsigned char *data);
void ivf_free(IVFContext *ivctx);
int ivf_read_frame(IVFContext *ivctx);

#endif /* __IVF_H__ */
