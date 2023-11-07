/*
 *  Copyright (c) 2010 The WebM project authors. All Rights Reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#include <stdint.h>
#include <limits.h>
#include <stddef.h>
#include <string.h>

#include "vpx_dsp_common.h"
#include "vpx_endian.h"
#include "vpx_rac.h"

static const uint8_t vpx_norm[256] = {
  0, 7, 6, 6, 5, 5, 5, 5, 4, 4, 4, 4, 4, 4, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
  3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
  2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
  1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
  1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0,
  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
};

void vpx_reader_fill(vpx_reader *r) {
  const uint8_t *const buffer_end = r->buffer_end;
  const uint8_t *buffer = r->buffer;
  const uint8_t *buffer_start = buffer;
  BD_VALUE value = r->value;
  int count = r->count;
  const size_t bytes_left = buffer_end - buffer;
  const size_t bits_left = bytes_left * CHAR_BIT;
  int shift = BD_VALUE_SIZE - CHAR_BIT - (count + CHAR_BIT);

  if (r->decrypt_cb) {
    size_t n = VPXMIN(sizeof(r->clear_buffer), bytes_left);
    r->decrypt_cb(r->decrypt_state, buffer, r->clear_buffer, (int)n);
    buffer = r->clear_buffer;
    buffer_start = r->clear_buffer;
  }
  if (bits_left > BD_VALUE_SIZE) {
    const int bits = (shift & 0xfffffff8) + CHAR_BIT;
    BD_VALUE nv;
    BD_VALUE big_endian_values;
    memcpy(&big_endian_values, buffer, sizeof(BD_VALUE));
#if SIZE_MAX == 0xffffffffffffffffULL
    big_endian_values = HToBE64(big_endian_values);
#else
    big_endian_values = HToBE32(big_endian_values);
#endif
    nv = big_endian_values >> (BD_VALUE_SIZE - bits);
    count += bits;
    buffer += (bits >> 3);
    value = r->value | (nv << (shift & 0x7));
  } else {
    const int bits_over = (int)(shift + CHAR_BIT - (int)bits_left);
    int loop_end = 0;
    if (bits_over >= 0) {
      count += LOTS_OF_BITS;
      loop_end = bits_over;
    }

    if (bits_over < 0 || bits_left) {
      while (shift >= loop_end) {
        count += CHAR_BIT;
        value |= (BD_VALUE)*buffer++ << shift;
        shift -= CHAR_BIT;
      }
    }
  }

  // NOTE: Variable 'buffer' may not relate to 'r->buffer' after decryption,
  // so we increase 'r->buffer' by the amount that 'buffer' moved, rather than
  // assign 'buffer' to 'r->buffer'.
  r->buffer += buffer - buffer_start;
  r->value = value;
  r->count = count;
}

const uint8_t *vpx_reader_find_end(vpx_reader *r) {
  // Find the end of the coded buffer
  while (r->count > CHAR_BIT && r->count < BD_VALUE_SIZE) {
    r->count -= CHAR_BIT;
    r->buffer--;
  }
  return r->buffer;
}

int vpx_read(vpx_reader *r, int prob) {
  unsigned int bit = 0;
  BD_VALUE value;
  BD_VALUE bigsplit;
  int count;
  unsigned int range;
  unsigned int split = (r->range * prob + (256 - prob)) >> CHAR_BIT;

  if (r->count < 0) vpx_reader_fill(r);

  value = r->value;
  count = r->count;

  bigsplit = (BD_VALUE)split << (BD_VALUE_SIZE - CHAR_BIT);

  range = split;

  if (value >= bigsplit) {
    range = r->range - split;
    value = value - bigsplit;
    bit = 1;
  }

  {
    const unsigned char shift = vpx_norm[(unsigned char)range];
    range <<= shift;
    value <<= shift;
    count -= shift;
  }
  r->value = value;
  r->count = count;
  r->range = range;

#if CONFIG_BITSTREAM_DEBUG
  {
    const int queue_r = bitstream_queue_get_read();
    const int frame_idx = bitstream_queue_get_frame_read();
    int ref_result, ref_prob;
    bitstream_queue_pop(&ref_result, &ref_prob);
    if ((int)bit != ref_result) {
      fprintf(stderr,
              "\n *** [bit] result error, frame_idx_r %d bit %d ref_result %d "
              "queue_r %d\n",
              frame_idx, bit, ref_result, queue_r);

      assert(0);
    }
    if (prob != ref_prob) {
      fprintf(stderr,
              "\n *** [bit] prob error, frame_idx_r %d prob %d ref_prob %d "
              "queue_r %d\n",
              frame_idx, prob, ref_prob, queue_r);

      assert(0);
    }
  }
#endif

  return bit;
}

int vpx_reader_init(vpx_reader *r, const uint8_t *buffer, size_t size,
                    vpx_decrypt_cb decrypt_cb, void *decrypt_state) {
  if (size && !buffer) {
    return 1;
  } else {
    r->buffer_end = buffer + size;
    r->buffer = buffer;
    r->value = 0;
    r->count = -8;
    r->range = 255;
    r->decrypt_cb = decrypt_cb;
    r->decrypt_state = decrypt_state;
    vpx_reader_fill(r);
    return vpx_read_bit(r) != 0;  // marker bit
  }
}
