/*
 * Copyright 2023 Eileen Yoon <eyn@gmx.com>
 *
 * Based on h264bitstream
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

#include "h2645.h"

int h2645_find_nal_unit(uint8_t *buf, int size, int *nal_start, int *nal_end)
{
	int i;
	*nal_start = 0;
	*nal_end = 0;

	i = 0;
	while ( // ( next_bits( 24 ) != 0x000001 && next_bits( 32 ) != 0x00000001 )
		(buf[i] != 0 || buf[i + 1] != 0 || buf[i + 2] != 0x01) &&
		(buf[i] != 0 || buf[i + 1] != 0 || buf[i + 2] != 0 ||
		 buf[i + 3] != 0x01)) {
		i++; // skip leading zero
		if (i + 4 >= size) {
			return 0;
		} // did not find nal start
	}

	if (buf[i] != 0 || buf[i + 1] != 0 ||
	    buf[i + 2] != 0x01) // ( next_bits( 24 ) != 0x000001 )
	{
		i++;
	}

	if (buf[i] != 0 || buf[i + 1] != 0 ||
	    buf[i + 2] != 0x01) { /* error, should never happen */
		return 0;
	}
	i += 3;
	*nal_start = i;

	while ( //( next_bits( 24 ) != 0x000000 && next_bits( 24 ) != 0x000001 )
		(buf[i] != 0 || buf[i + 1] != 0 || buf[i + 2] != 0) &&
		(buf[i] != 0 || buf[i + 1] != 0 || buf[i + 2] != 0x01)) {
		i++;
		// FIXME the next line fails when reading a nal that ends exactly at the end of the data
		if (i + 3 >= size) {
			*nal_end = size;
			return -1;
		} // did not find nal end, stream ended first
	}

	*nal_end = i;
	return (*nal_end - *nal_start);
}

int h2645_nal_to_rbsp(const uint8_t *nal_buf, int *nal_size, uint8_t *rbsp_buf, int *rbsp_size)
{
	int i;
	int j = 0;
	int count = 0;

	for (i = 0; i < *nal_size; i++) {
		// in NAL unit, 0x000000, 0x000001 or 0x000002 shall not occur at any byte-aligned position
		if ((count == 2) && (nal_buf[i] < 0x03)) {
			return -1;
		}

		if ((count == 2) && (nal_buf[i] == 0x03)) {
			// check the 4th byte after 0x000003, except when cabac_zero_word is used, in which case the last three bytes of this NAL unit must be 0x000003
			if ((i < *nal_size - 1) && (nal_buf[i + 1] > 0x03)) {
				return -1;
			}

			// if cabac_zero_word is used, the final byte of this NAL unit(0x03) is discarded, and the last two bytes of RBSP must be 0x0000
			if (i == *nal_size - 1) {
				break;
			}

			i++;
			count = 0;
		}

		if (j >= *rbsp_size) {
			// error, not enough space
			return -1;
		}

		rbsp_buf[j] = nal_buf[i];
		if (nal_buf[i] == 0x00) {
			count++;
		} else {
			count = 0;
		}
		j++;
	}

	*nal_size = i;
	*rbsp_size = j;
	return j;
}

int h2645_more_rbsp_data(struct bitstream *gb)
{
	struct bitstream bs_tmp;

	/* No more data */
	if (bs_eof(gb))
		return 0;

	/* No rbsp_stop_bit yet */
	if (bs_peek_u1(gb) == 0)
		return -1;

	/* Next bit is 1, is it the rsbp_stop_bit? only if the rest of bits are 0 */
	bs_clone(&bs_tmp, gb);
	bs_skip_u1(&bs_tmp);
	while (!bs_eof(&bs_tmp)) {
		// A later bit was 1, it wasn't the rsbp_stop_bit
		if (bs_read_u1(&bs_tmp) == 1) {
			return -1;
		}
	}

	/* All following bits were 0, it was the rsbp_stop_bit */
	return 0;
}

void h2645_rbsp_trailing_bits(struct bitstream *gb)
{
	skip_bits1(gb); /* rbsp_stop_one_bit */
	while (!bs_byte_aligned(gb))
		skip_bits1(gb); /* rbsp_alignment_zero_bit */
}
