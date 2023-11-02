/* 
 * h264bitstream - a library for reading and writing H.264 video
 * Copyright (C) 2005-2007 Auroras Entertainment, LLC
 * Copyright (C) 2008-2011 Avail-TVN
 * 
 * Written by Alex Izvorski <aizvorski@gmail.com> and Alex Giladi <alex.giladi@gmail.com>
 * 
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 * 
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 * 
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 */

#ifndef _H264_BS_H
#define _H264_BS_H        1

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

struct bitstream {
	uint8_t* start;
	uint8_t* p;
	uint8_t* end;
	int bits_left;
};
typedef struct bitstream bs_t;

#define _OPTIMIZE_BS_ 1
#if ( _OPTIMIZE_BS_ > 0 )
#ifndef FAST_U8
#define FAST_U8
#endif
#endif

static inline bs_t* bs_new(uint8_t* buf, size_t size);
static inline void bs_free(bs_t* b);
static inline bs_t* bs_clone( bs_t* dest, const bs_t* src );
static inline void  bs_init(bs_t* b, uint8_t* buf, size_t size);
static inline uint32_t bs_byte_aligned(bs_t* b);
static inline int bs_eof(bs_t* b);
static inline int bs_overrun(bs_t* b);
static inline int bs_pos(bs_t* b);

static inline uint32_t bs_peek_u1(bs_t* b);
static inline uint32_t bs_read_u1(bs_t* b);
static inline uint32_t bs_read_u(bs_t* b, int n);
static inline uint32_t bs_read_f(bs_t* b, int n);
static inline uint32_t bs_read_u8(bs_t* b);
static inline uint32_t bs_read_ue(bs_t* b);
static inline int32_t  bs_read_se(bs_t* b);
static inline void     bs_skip_u(bs_t* b, int n);
static inline void     bs_skip_u1(bs_t* b);

#define get_bits(gb, n)        (bs_read_u(gb, n))
#define skip_bits(gb, n)       (bs_skip_u(gb, n))
#define get_bits1(gb)          (bs_read_u1(gb))
#define skip_bits1(gb)         (bs_skip_u1(gb))

#define get_ue_golomb(gb)      (bs_read_ue(gb))
#define get_se_golomb(gb)      (bs_read_se(gb))
#define get_ue_golomb_long(gb) (bs_read_ue(gb))
#define get_se_golomb_long(gb) (bs_read_se(gb))
#define get_ue_golomb_31(gb)   (bs_read_ue(gb))

static inline int decode012(struct bitstream *gb)
{
    int n;
    n = get_bits1(gb);
    if (n == 0)
        return 0;
    else
        return get_bits1(gb) + 1;
}

static inline int decode210(struct bitstream *gb)
{
    if (get_bits1(gb))
        return 0;
    else
        return 2 - get_bits1(gb);
}

static inline int get_bits_count(struct bitstream *gb)
{
    return gb->bits_left;
}

static inline void trailing_bits(struct bitstream *gb)
{
	while (!bs_byte_aligned(gb)) {
		skip_bits1(gb);
	}
}

// IMPLEMENTATION

static inline void bs_init(bs_t* b, uint8_t* buf, size_t size)
{
    b->start = buf;
    b->p = buf;
    b->end = buf + size;
    b->bits_left = 8;
}

static inline bs_t* bs_new(uint8_t* buf, size_t size)
{
    bs_t* b = (bs_t*)malloc(sizeof(bs_t));
    bs_init(b, buf, size);
    return b;
}

static inline void bs_free(bs_t* b)
{
    free(b);
}

static inline bs_t* bs_clone(bs_t* dest, const bs_t* src)
{
    dest->start = src->p;
    dest->p = src->p;
    dest->end = src->end;
    dest->bits_left = src->bits_left;
    return dest;
}

static inline uint32_t bs_byte_aligned(bs_t* b) 
{ 
    return (b->bits_left == 8);
}

static inline int bs_eof(bs_t* b) { if (b->p >= b->end) { return 1; } else { return 0; } }

static inline int bs_overrun(bs_t* b) { if (b->p > b->end) { return 1; } else { return 0; } }

static inline int bs_pos(bs_t* b) { if (b->p > b->end) { return (b->end - b->start); } else { return (b->p - b->start); } }

static inline int bs_bytes_left(bs_t* b) { return (b->end - b->p); }

static inline uint32_t bs_read_u1(bs_t* b)
{
    uint32_t r = 0;
    
    b->bits_left--;

    if (! bs_eof(b))
    {
        r = ((*(b->p)) >> b->bits_left) & 0x01;
    }

    if (b->bits_left == 0) { b->p ++; b->bits_left = 8; }

    return r;
}

static inline void bs_skip_u1(bs_t* b)
{    
    b->bits_left--;
    if (b->bits_left == 0) { b->p ++; b->bits_left = 8; }
}

static inline uint32_t bs_peek_u1(bs_t* b)
{
    uint32_t r = 0;

    if (! bs_eof(b))
    {
        r = ((*(b->p)) >> ( b->bits_left - 1 )) & 0x01;
    }
    return r;
}


static inline uint32_t bs_read_u(bs_t* b, int n)
{
    uint32_t r = 0;
    int i;
    for (i = 0; i < n; i++)
    {
        r |= ( bs_read_u1(b) << ( n - i - 1 ) );
    }
    return r;
}

static inline void bs_skip_u(bs_t* b, int n)
{
    int i;
    for ( i = 0; i < n; i++ ) 
    {
        bs_skip_u1( b );
    }
}

static inline uint32_t bs_read_f(bs_t* b, int n) { return bs_read_u(b, n); }

static inline uint32_t bs_read_u8(bs_t* b)
{
#ifdef FAST_U8
    if (b->bits_left == 8 && ! bs_eof(b)) // can do fast read
    {
        uint32_t r = b->p[0];
        b->p++;
        return r;
    }
#endif
    return bs_read_u(b, 8);
}

static inline uint32_t bs_read_ue(bs_t* b)
{
    int32_t r = 0;
    int i = 0;

    while( (bs_read_u1(b) == 0) && (i < 32) && (!bs_eof(b)) )
    {
        i++;
    }
    r = bs_read_u(b, i);
    r += (1 << i) - 1;
    return r;
}

static inline int32_t bs_read_se(bs_t* b) 
{
    int32_t r = bs_read_ue(b);
    if (r & 0x01)
    {
        r = (r+1)/2;
    }
    else
    {
        r = -(r/2);
    }
    return r;
}


static inline void bs_write_u1(bs_t* b, uint32_t v)
{
    b->bits_left--;

    if (! bs_eof(b))
    {
        // FIXME this is slow, but we must clear bit first
        // is it better to memset(0) the whole buffer during bs_init() instead? 
        // if we don't do either, we introduce pretty nasty bugs
        (*(b->p)) &= ~(0x01 << b->bits_left);
        (*(b->p)) |= ((v & 0x01) << b->bits_left);
    }

    if (b->bits_left == 0) { b->p ++; b->bits_left = 8; }
}

static inline void bs_write_u(bs_t* b, int n, uint32_t v)
{
    int i;
    for (i = 0; i < n; i++)
    {
        bs_write_u1(b, (v >> ( n - i - 1 ))&0x01 );
    }
}

static inline void bs_write_f(bs_t* b, int n, uint32_t v) { bs_write_u(b, n, v); }

static inline void bs_write_u8(bs_t* b, uint32_t v)
{
#ifdef FAST_U8
    if (b->bits_left == 8 && ! bs_eof(b)) // can do fast write
    {
        b->p[0] = v;
        b->p++;
        return;
    }
#endif
    bs_write_u(b, 8, v);
}

static inline void bs_write_ue(bs_t* b, uint32_t v)
{
    static const int len_table[256] =
    {
        1,
        1,
        2,2,
        3,3,3,3,
        4,4,4,4,4,4,4,4,
        5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,
        6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,
        6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,
        7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
        7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
        7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
        7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
        8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,
        8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,
        8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,
        8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,
        8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,
        8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,
        8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,
        8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,
    };

    int len;

    if (v == 0)
    {
        bs_write_u1(b, 1);
    }
    else
    {
        v++;

        if (v >= 0x01000000)
        {
            len = 24 + len_table[ v >> 24 ];
        }
        else if(v >= 0x00010000)
        {
            len = 16 + len_table[ v >> 16 ];
        }
        else if(v >= 0x00000100)
        {
            len =  8 + len_table[ v >>  8 ];
        }
        else 
        {
            len = len_table[ v ];
        }

        bs_write_u(b, 2*len-1, v);
    }
}

static inline void bs_write_se(bs_t* b, int32_t v)
{
    if (v <= 0)
    {
        bs_write_ue(b, -v*2);
    }
    else
    {
        bs_write_ue(b, v*2 - 1);
    }
}

static inline int bs_read_bytes(bs_t* b, uint8_t* buf, int len)
{
    int actual_len = len;
    if (b->end - b->p < actual_len) { actual_len = b->end - b->p; }
    if (actual_len < 0) { actual_len = 0; }
    memcpy(buf, b->p, actual_len);
    if (len < 0) { len = 0; }
    b->p += len;
    return actual_len;
}

static inline int bs_write_bytes(bs_t* b, uint8_t* buf, int len)
{
    int actual_len = len;
    if (b->end - b->p < actual_len) { actual_len = b->end - b->p; }
    if (actual_len < 0) { actual_len = 0; }
    memcpy(b->p, buf, actual_len);
    if (len < 0) { len = 0; }
    b->p += len;
    return actual_len;
}

static inline int bs_skip_bytes(bs_t* b, int len)
{
    int actual_len = len;
    if (b->end - b->p < actual_len) { actual_len = b->end - b->p; }
    if (actual_len < 0) { actual_len = 0; }
    if (len < 0) { len = 0; }
    b->p += len;
    return actual_len;
}

static inline uint32_t bs_next_bits(bs_t* bs, int nbits)
{
   bs_t b;
   bs_clone(&b,bs);
   return bs_read_u(&b, nbits);
}

static inline uint64_t bs_next_bytes(bs_t* bs, int nbytes)
{
   int i = 0;
   uint64_t val = 0;

   if ( (nbytes > 8) || (nbytes < 1) ) { return 0; }
   if (bs->p + nbytes > bs->end) { return 0; }

   for ( i = 0; i < nbytes; i++ ) { val = ( val << 8 ) | bs->p[i]; }
   return val;
}

#define bs_print_state(b) fprintf( stderr,  "%s:%d@%s: b->p=0x%02hhX, b->left = %d\n", __FILE__, __LINE__, __FUNCTION__, *b->p, b->bits_left )

#ifdef __cplusplus
}
#endif

#endif
