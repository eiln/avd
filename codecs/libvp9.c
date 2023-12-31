
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

#include <stdio.h>
#include <stdlib.h>
#include "vp9.h"

typedef struct __attribute__((packed)) LibVP9Context {
	VP9ProbContext p;
	VP9Context *s;
} LibVP9Context;

void *libvp9_init(void)
{
	LibVP9Context *ctx = malloc(sizeof(*ctx));
	if (!ctx)
		return NULL;
	ctx->s = malloc(sizeof(*ctx->s));
	if (!ctx->s) {
		free(ctx);
		return NULL;
	}
	memset(ctx->s, 0, sizeof(*ctx->s));
	return (void *)ctx;
}

void libvp9_free(void *handle)
{
	LibVP9Context *ctx = handle;
	free(ctx->s);
	free(ctx);
}

int libvp9_decode(void *handle, const uint8_t *buf, int size, int do_probs)
{
	LibVP9Context *ctx = handle;
	VP9Context *s = ctx->s;
	int err;

	err = vp9_decode_uncompressed_header(s, buf, size);
	if (err){
		fprintf(stderr, "[LIBVP9] failed to decode uncompressed header\n");
		return err;
	}

	err = vp9_decode_compressed_header(s, buf, s->s.h.compressed_header_size);
	if (err){
		fprintf(stderr, "[LIBVP9] failed to decode compressed header\n");
		return err;
	}

	if (do_probs)
		ctx->p = s->prob.p;

	vp9_print_header(s);

	if (do_probs)
		vp9_adapt_probs(s);

	return 0;
}
