#ifndef ANIA_FAST_DECODE_H
#define ANIA_FAST_DECODE_H
#include <stdint.h>
#include <stddef.h>
struct fast_frame { uint8_t raw[19]; uint8_t len,quality; uint32_t sample; };
/* Scratch: n floats for discriminator; ceil(n/4) floats for chips. */
int fast_decode(const int8_t *iq,size_t n,float *disc,float *chips,struct fast_frame *out,size_t cap);
#endif
