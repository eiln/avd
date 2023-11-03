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

#include "h264.h"
#include "util.h"

int main(int argc, char *argv[])
{
	int bytesnum, err;
	if (argc <= 1) {
		fprintf(stderr, "usage: ./deh264 [path to .h264]\n");
		return -1;
	}
	char *data = read_file(argv[1], &bytesnum);
	uint8_t *bytes = (uint8_t *)data;
	if (!data || !bytesnum)
		return -1;

	struct h264_decoder decoder;
	struct h264_decoder *dec = &decoder;
	int nal_start, nal_end;
	while (bytesnum > 0) {
		h264_find_nal_unit(bytes, bytesnum, &nal_start, &nal_end);
		bytes += nal_start;
		h264_decode_nal_unit(dec, bytes, nal_end - nal_start);
		bytes += (nal_end - nal_start);
		bytesnum -= nal_end;
	}

	free(data);

	return 0;
}
