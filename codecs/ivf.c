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

#include "ivf.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define IVF_SIGNATURE 0x46494b44 /* DKIF */

static inline unsigned int avio_r8(unsigned char **b)
{
	return *(*b)++;
}

static inline unsigned int avio_rl16(unsigned char **b)
{
	unsigned int val;
	val = avio_r8(b);
	val |= avio_r8(b) << 8;
	return val;
}

static inline uint32_t avio_rl32(unsigned char **b)
{
	uint32_t val;
	val = avio_rl16(b);
	val |= avio_rl16(b) << 16;
	return val;
}

static inline uint64_t avio_rl64(unsigned char **b)
{
	uint64_t val;
	val = (uint64_t)avio_rl32(b);
	val |= (uint64_t)avio_rl32(b) << 32;
	return val;
}

struct ivf_context *ivf_init(unsigned char *data)
{
	struct ivf_context *ivctx;
	struct ivf_header *h;

	ivctx = malloc(sizeof(*ivctx));
	if (!ivctx)
		return NULL;

	ivctx->start = data;
	ivctx->p = data;
	ivctx->fnum = 0;

	h = &ivctx->h;
	memcpy(h, ivctx->p, sizeof(*h));

	if (h->signature != IVF_SIGNATURE || !!h->version || h->length != 32)
		goto err;

	printf("[IVF] codec: %c%c%c%c, %dx%d, frames: %d\n", h->fourcc[0], h->fourcc[1],
	       h->fourcc[2], h->fourcc[3], h->width, h->height, h->frame_count);
	ivctx->p += sizeof(*h);

	return ivctx;

err:
	free(ivctx);
	return NULL;
}

void ivf_free(struct ivf_context *ivctx)
{
	free(ivctx);
}

int ivf_read_frame(struct ivf_context *ivctx)
{
	struct ivf_frame *f = &ivctx->f;
	if (ivctx->fnum >= ivctx->h.frame_count) {
		printf("[IVF] reached end of stream\n");
		return -1;
	}

	f->size = avio_rl32(&ivctx->p);
	f->timestamp = avio_rl64(&ivctx->p);
	f->buf = ivctx->p;
	printf("[IVF] frame %d: size: %d timestamp: %d\n", ivctx->fnum, f->size,
	       f->timestamp);

	ivctx->fnum++;
	ivctx->p += f->size;

	return 0;
}
