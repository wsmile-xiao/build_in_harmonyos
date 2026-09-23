#include <murmurhash.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    static const char input_a[] = "hello-murmur";
    static const char input_b[] = "hello-murmur!";
    uint32_t h32_a1 = 0;
    uint32_t h32_a2 = 0;
    uint32_t h32_seed = 0;
    uint32_t h32_b = 0;
    uint32_t h32_empty = 0;
    uint32_t h128_a1[4] = {0, 0, 0, 0};
    uint32_t h128_a2[4] = {0, 0, 0, 0};
    uint64_t h64_a1[2] = {0, 0};
    uint64_t h64_a2[2] = {0, 0};
    uint32_t old_hash = 0;

    /* x86_32 determinism: same input and seed give the same hash. */
    lmmh_x86_32(input_a, (unsigned int)strlen(input_a), 0, &h32_a1);
    lmmh_x86_32(input_a, (unsigned int)strlen(input_a), 0, &h32_a2);
    if (h32_a1 != h32_a2)
        return 1;

    /* Seed sensitivity: a different seed must change the hash. */
    lmmh_x86_32(input_a, (unsigned int)strlen(input_a), 42, &h32_seed);
    if (h32_seed == h32_a1)
        return 2;

    /* Input sensitivity: a different input must change the hash. */
    lmmh_x86_32(input_b, (unsigned int)strlen(input_b), 0, &h32_b);
    if (h32_b == h32_a1)
        return 3;

    /* x86_128 determinism. */
    lmmh_x86_128(input_a, (unsigned int)strlen(input_a), 0, h128_a1);
    lmmh_x86_128(input_a, (unsigned int)strlen(input_a), 0, h128_a2);
    if (memcmp(h128_a1, h128_a2, sizeof(h128_a1)) != 0)
        return 4;
    if (h128_a1[0] == 0 && h128_a1[1] == 0 && h128_a1[2] == 0 && h128_a1[3] == 0)
        return 5;

    /* x64_128 determinism. */
    lmmh_x64_128(input_a, (unsigned int)strlen(input_a), 0, h64_a1);
    lmmh_x64_128(input_a, (unsigned int)strlen(input_a), 0, h64_a2);
    if (memcmp(h64_a1, h64_a2, sizeof(h64_a1)) != 0)
        return 6;
    if (h64_a1[0] == 0 && h64_a1[1] == 0)
        return 7;

    /* Deprecated original API still works and agrees with the new one. */
    MurmurHash3_x86_32(input_a, (int)strlen(input_a), 0, &old_hash);
    if (old_hash != h32_a1)
        return 8;

    /* Zero-length input is accepted and deterministic. */
    lmmh_x86_32(input_a, 0, 0, &h32_empty);
    lmmh_x86_32(input_a, 0, 0, &h32_a2);
    if (h32_empty != h32_a2)
        return 9;

    printf("libmurmurhash 1.6 smoke test passed\n");
    return 0;
}
