/*
 * Copyright (C) 2010-2011 Marcelina Kościelnicka <mwk@0x04.net>
 * Copyright (C) 2010 Francisco Jerez <currojerez@riseup.net>
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

#ifndef __UTIL_H__
#define __UTIL_H__

#include <stdio.h>
#include <stdlib.h>

/* ceil log2 */
static inline int clog2(uint64_t x) {
	if (!x)
		return x;
	int r = 0;
	while (x - 1 > (1ull << r) - 1)
		r++;
	return r;
}

#define ARRAY_SIZE(a) (sizeof (a) / sizeof *(a))

#ifndef __cplusplus

#define min(a,b)				\
	({					\
		typeof (a) _a = (a);		\
		typeof (b) _b = (b);		\
		_a < _b ? _a : _b;		\
	})

#define max(a,b)				\
	({					\
		typeof (a) _a = (a);		\
		typeof (b) _b = (b);		\
		_a > _b ? _a : _b;		\
	})

#endif

#define CEILDIV(a, b) (((a) + (b) - 1)/(b))

#define extr(a, b, c) ((uint64_t)(a) << (64 - (b) - (c)) >> (64 - (c)))
#define extrs(a, b, c) ((int64_t)(a) << (64 - (b) - (c)) >> (64 - (c))) 
#define sext(a, b) extrs((a), 0, (b)+1)
#define bflmask(a) ((2ull << ((a)-1)) - 1)
#define insrt(a, b, c, d) ((a) = ((a) & ~(bflmask(c) << (b))) | ((d) & bflmask(c)) << (b))

static inline char *read_file(const char *path, int *size)
{
	char *data;
	int fsize;

	FILE *fp = fopen(path, "rb");
	if (!fp)
		return NULL;

	fseek(fp, 0, SEEK_END);
	fsize = ftell(fp);
	fseek(fp, 0, SEEK_SET);
	if (!fsize) {
		fclose(fp);
		return NULL;
	}

	data = malloc(fsize);
	if (!data) {
		fclose(fp);
		return NULL;
	}

	fread(data, fsize, 1, fp);
	fclose(fp);

	*size = fsize;
	return data;
}

static inline int write_to_file(const char *path, char *data, int size)
{
	FILE *fp = fopen(path, "wb");
	if (!fp)
		return -1;
	fwrite(data, size, 1, fp);
	fclose(fp);
	return 0;
}

#endif /* __UTIL_H__ */
