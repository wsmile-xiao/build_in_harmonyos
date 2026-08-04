#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bit_array.h"

#define REQUIRE(expr) do { \
  if (!(expr)) { \
    fprintf(stderr, "assertion failed: %s at %s:%d\n", #expr, __FILE__, __LINE__); \
    return EXIT_FAILURE; \
  } \
} while (0)

int main(void)
{
  BIT_ARRAY *bits = bit_array_create(16);
  REQUIRE(bits != NULL);
  REQUIRE(bit_array_length(bits) == 16);

  bit_array_set_bits(bits, 4, 1, 3, 8, 9);
  REQUIRE(bit_array_get_bit(bits, 1) == 1);
  REQUIRE(bit_array_get_bit(bits, 2) == 0);
  REQUIRE(bit_array_num_bits_set(bits) == 4);
  REQUIRE(bit_array_num_bits_cleared(bits) == 12);

  bit_index_t index = 0;
  REQUIRE(bit_array_find_first_set_bit(bits, &index) == 1);
  REQUIRE(index == 1);
  REQUIRE(bit_array_find_last_set_bit(bits, &index) == 1);
  REQUIRE(index == 9);

  bit_array_toggle_region(bits, 0, 4);
  REQUIRE(bit_array_get_bit(bits, 0) == 1);
  REQUIRE(bit_array_get_bit(bits, 1) == 0);
  REQUIRE(bit_array_get_bit(bits, 2) == 1);
  REQUIRE(bit_array_get_bit(bits, 3) == 0);
  REQUIRE(bit_array_num_bits_set(bits) == 4);

  uint64_t low_word = bit_array_get_wordn(bits, 0, 10);
  REQUIRE(low_word == 0x305);

  BIT_ARRAY *clone = bit_array_clone(bits);
  REQUIRE(clone != NULL);
  REQUIRE(bit_array_cmp(bits, clone) == 0);

  bit_array_shift_left(clone, 1, 0);
  REQUIRE(bit_array_cmp(bits, clone) != 0);
  bit_array_free(clone);

  BIT_ARRAY *parsed = bit_array_create(6);
  REQUIRE(parsed != NULL);
  bit_array_from_str(parsed, "101001");
  REQUIRE(bit_array_length(parsed) == 6);
  REQUIRE(bit_array_get_bit(parsed, 0) == 1);
  REQUIRE(bit_array_get_bit(parsed, 1) == 0);
  REQUIRE(bit_array_get_bit(parsed, 5) == 1);

  char out[16] = {0};
  bit_array_to_substr(parsed, 0, 6, out, '1', '0', 1);
  out[6] = '\0';
  REQUIRE(strcmp(out, "101001") == 0);
  bit_array_free(parsed);

  bit_array_from_decimal(bits, "12345");
  char decimal[32] = {0};
  REQUIRE(bit_array_to_decimal(bits, decimal, sizeof(decimal)) > 0);
  REQUIRE(strcmp(decimal, "12345") == 0);

  bit_array_free(bits);
  return EXIT_SUCCESS;
}
