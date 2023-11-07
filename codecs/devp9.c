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

#include "vp9.h"
#include "ivf.h"
#include "util.h"

int main(int argc, char *argv[])
{
	int i, err;
	if (argc <= 1) {
		fprintf(stderr, "usage: ./devp9 [path to .ivf] [optional count]\n");
		return -1;
	}
	int size;
	char *data = read_file(argv[1], &size);
	if (!data)
		return -1;

	int num = 1;
	if (argc >= 3) {
		num = atoi(argv[2]);
	}

	struct ivf_context *ivctx = ivf_init(data);
	if (!ivctx || (*(uint32_t *)ivctx->h.fourcc != FOURCC_VP90))
		goto free_data;

	VP9Context context;
	VP9Context *s = &context;
	memset(s, 0, sizeof(*s));
	char* path;
	for (i = 0; i < num; i++) {
		err = ivf_read_frame(ivctx);
		if (err)
			goto free_ivf;

		err = vp9_decode_uncompressed_header(s, ivctx->f.buf, ivctx->f.size);
		err = vp9_decode_compressed_header(s, ivctx->f.buf, s->s.h.compressed_header_size);

		vp9_print_header(s);
		asprintf(&path, "out/p%d.bin", i);
		vp9_save_probs(s, path);
		vp9_adapt_probs(s);
	}

free_ivf:
	ivf_free(ivctx);
free_data:
	free(data);
	return 0;
}
