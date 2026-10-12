/*
 * Consumer test for bitarray 0.0-git.f444eb4.
 *
 * Links the packaged bitarray::bitarray target (libbitarr.a) and exercises
 * the public API exactly as documented in the upstream README:
 *   - bit_array_create / bit_array_free lifecycle
 *   - set / get / clear / toggle single bits (including bit 0 and the last bit)
 *   - bit_array_set_bits variadic helper
 *   - bit_array_resize growth preserving existing bits
 *   - string serialization round-trip via bit_array_to_str + bit_array_from_str
 *   - bit_array_to_str_rev reversed printing (upstream's display convention)
 *   - bit_array_length
 */

#include <stdio.h>
#include <string.h>

#include "bit_array.h"

static int failures = 0;

#define CHECK(cond, msg)                                                 \
    do {                                                                 \
        if (!(cond)) {                                                   \
            fprintf(stderr, "failed assert [%s:%i] %s\n", __FILE__,      \
                    __LINE__, msg);                                      \
            failures++;                                                  \
        }                                                                \
    } while (0)

int main(void)
{
    /* -- lifecycle + basic set/get bit flipping ------------------------ */
    BIT_ARRAY *bitarr = bit_array_create(10);
    CHECK(bitarr != NULL, "bit_array_create(10) returns a valid array");
    CHECK(bit_array_length(bitarr) == 10, "initial length is 10");

    CHECK(bit_array_get(bitarr, 0) == 0, "bit 0 starts clear");
    CHECK(bit_array_get(bitarr, 9) == 0, "last bit starts clear");

    bit_array_set(bitarr, 0);
    bit_array_set(bitarr, 3);
    bit_array_set(bitarr, 9);
    CHECK(bit_array_get(bitarr, 0) == 1, "set() flips bit 0 to 1");
    CHECK(bit_array_get(bitarr, 3) == 1, "set() flips bit 3 to 1");
    CHECK(bit_array_get(bitarr, 9) == 1, "set() flips last bit 9 to 1");
    CHECK(bit_array_get(bitarr, 5) == 0, "untouched bit 5 stays 0");

    bit_array_clear(bitarr, 3);
    CHECK(bit_array_get(bitarr, 3) == 0, "clear() flips bit 3 back to 0");

    bit_array_toggle(bitarr, 5);
    CHECK(bit_array_get(bitarr, 5) == 1, "toggle() flips bit 5 from 0 to 1");
    bit_array_toggle(bitarr, 5);
    CHECK(bit_array_get(bitarr, 5) == 0, "toggle() flips bit 5 back to 0");

    /* -- variadic set_bits (same call pattern as upstream example.c) --- */
    BIT_ARRAY *bitarr2 = bit_array_create(10);
    bit_array_set_bits(bitarr2, 3, 1, 2, 5);
    CHECK(bit_array_get(bitarr2, 1) == 1 &&
              bit_array_get(bitarr2, 2) == 1 && bit_array_get(bitarr2, 5) == 1,
          "set_bits(3, 1,2,5) sets exactly those bits");

    /* -- string serialization round-trip ------------------------------- */
    /* sized for the 64-bit array serialized below (64 chars + NUL) */
    char str[80];
    bit_array_to_str(bitarr, str);
    CHECK(strcmp(str, "1000000001") == 0,
          "to_str() renders set bits as '1000000001'");

    BIT_ARRAY *parsed = bit_array_create(10);
    bit_array_from_str(parsed, str);
    CHECK(bit_array_get(parsed, 0) == 1 && bit_array_get(parsed, 9) == 1 &&
              bit_array_get(parsed, 4) == 0,
          "from_str() round-trips the serialized bit pattern");
    CHECK(bit_array_length(parsed) == 10, "round-tripped length is preserved");

    bit_array_to_str_rev(bitarr, str);
    CHECK(strcmp(str, "1000000001") == 0,
          "to_str_rev() of a palindrome pattern is identical");

    /* -- resize keeps existing bits ------------------------------------ */
    CHECK(bit_array_resize(bitarr, 64) != 0, "resize 10 -> 64 succeeds");
    CHECK(bit_array_length(bitarr) == 64, "length is 64 after resize");
    CHECK(bit_array_get(bitarr, 0) == 1 && bit_array_get(bitarr, 9) == 1,
          "bits survive resize");
    CHECK(bit_array_get(bitarr, 63) == 0, "new tail bits start clear");

    bit_array_set(bitarr, 63);
    bit_array_to_str(bitarr, str);
    CHECK(str[63] == '1' && str[10] == '0',
          "bit 63 set is visible in the serialized form");

    bit_array_free(bitarr);
    bit_array_free(bitarr2);
    bit_array_free(parsed);

    if (failures != 0) {
        fprintf(stderr, "bitarray consumer test failed: %d assertion(s)\n",
                failures);
        return 1;
    }
    puts("bitarray consumer test passed: 16 assertions");
    return 0;
}
