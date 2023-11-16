
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

#include "h264.h"
#include "h2645.h"

typedef struct __attribute__((packed)) LibH264Context {
	struct h264_context *s;
} LibH264Context;

LibH264Context *libh264_init(void)
{
	LibH264Context *ctx = malloc(sizeof(*ctx));
	if (!ctx)
		return NULL;
	ctx->s = malloc(sizeof(*ctx->s));
	if (!ctx->s) {
		free(ctx);
		return NULL;
	}
	return ctx;
}

void libh264_free(LibH264Context *ctx)
{
	free(ctx->s);
	free(ctx);
}

int libh264_decode(LibH264Context *ctx, uint8_t *bytes, int size, int *nal_start, int *nal_end)
{
	int err;

	if (!bytes || size < 0)
		return -1;

	h2645_find_nal_unit(bytes, size, nal_start, nal_end);
	if (size < (*nal_end - *nal_start)) {
		fprintf(stderr, "[LIBH264] no more NAL units left\n");
		return -1;
	}

	bytes += *nal_start; /* move up to RBSP */
	err = h264_decode_nal_unit(ctx->s, bytes, *nal_end - *nal_start);
	if (err < 0) {
		fprintf(stderr, "[LIBH264] failed to find NAL unit\n");
		return -1;
	}

	return 0;
}
