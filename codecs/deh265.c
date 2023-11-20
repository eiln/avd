/*
 * Copyright 2023 Eileen Yoon <eyn@gmx.com>
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

#include "h265.h"
#include "h2645.h"
#include "util.h"

int main(int argc, char *argv[])
{
	struct h265_context *ctx = NULL;
	int size, nal_start, nal_end;

	uint8_t *bytes = NULL;
	char *data = NULL;
	if (argc <= 1) {
		fprintf(stderr, "usage: ./deh265 [path to .h265]\n");
		return -1;
	}

	data = read_file(argv[1], &size);
	if (!data || size <= 0)
		return -1;

	ctx = malloc(sizeof(*ctx));
	if (!ctx)
		goto free_data;

	bytes = (uint8_t *)data;
	while (size > 0) {
		h2645_find_nal_unit(bytes, size, &nal_start, &nal_end);
		bytes += nal_start;
		h265_decode_nal_unit(ctx, bytes, nal_end - nal_start);
		bytes += (nal_end - nal_start);
		size -= nal_end;
	}

	free(ctx);
free_data:
	free(data);

	return 0;
}
