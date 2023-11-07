/*
 *  Copyright (c) 2010 The WebM project authors. All Rights Reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#ifndef VPX_VPX_DSP_BITREADER_H_
#define VPX_VPX_DSP_BITREADER_H_

#include <stddef.h>
#include <stdio.h>
#include <limits.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef size_t BD_VALUE;
#define BD_VALUE_SIZE ((int)sizeof(BD_VALUE) * CHAR_BIT)

// This is meant to be a large, positive constant that can still be efficiently
// loaded as an immediate (on platforms like ARM, for example).
// Even relatively modest values like 100 would work fine.
#define LOTS_OF_BITS 0x40000000

typedef void (*vpx_decrypt_cb)(void *decrypt_state, const unsigned char *input,
                               unsigned char *output, int count);

typedef struct {
  // Be careful when reordering this struct, it may impact the cache negatively.
  BD_VALUE value;
  unsigned int range;
  int count;
  const uint8_t *buffer_end;
  const uint8_t *buffer;
  vpx_decrypt_cb decrypt_cb;
  void *decrypt_state;
  uint8_t clear_buffer[sizeof(BD_VALUE) + 1];
} vpx_reader;
typedef vpx_reader VPXRangeCoder;

int vpx_reader_init(vpx_reader *r, const uint8_t *buffer, size_t size,
                    vpx_decrypt_cb decrypt_cb, void *decrypt_state);
int vpx_read(vpx_reader *r, int prob);
void vpx_reader_fill(vpx_reader *r);

const uint8_t *vpx_reader_find_end(vpx_reader *r);

static inline int vpx_reader_has_error(vpx_reader *r) {
  // Check if we have reached the end of the buffer.
  //
  // Variable 'count' stores the number of bits in the 'value' buffer, minus
  // 8. The top byte is part of the algorithm, and the remainder is buffered
  // to be shifted into it. So if count == 8, the top 16 bits of 'value' are
  // occupied, 8 for the algorithm and 8 in the buffer.
  //
  // When reading a byte from the user's buffer, count is filled with 8 and
  // one byte is filled into the value buffer. When we reach the end of the
  // data, count is additionally filled with LOTS_OF_BITS. So when
  // count == LOTS_OF_BITS - 1, the user's data has been exhausted.
  //
  // 1 if we have tried to decode bits after the end of stream was encountered.
  // 0 No error.
  return r->count > BD_VALUE_SIZE && r->count < LOTS_OF_BITS;
}

static inline int vpx_read_bit(vpx_reader *r) {
  return vpx_read(r, 128);  // vpx_prob_half
}

static inline int vpx_read_literal(vpx_reader *r, int bits) {
  int literal = 0, bit;

  for (bit = bits - 1; bit >= 0; bit--) literal |= vpx_read_bit(r) << bit;

  return literal;
}

static inline int vpx_read_tree(vpx_reader *r, const int8_t *tree,
                                const uint8_t *probs) {
  int8_t i = 0;

  while ((i = tree[i + vpx_read(r, probs[i >> 1])]) > 0) continue;

  return -i;
}

#ifdef __cplusplus
}  // extern "C"
#endif

#endif  // VPX_VPX_DSP_BITREADER_H_
