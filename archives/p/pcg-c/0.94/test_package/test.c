#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

#include <pcg_variants.h>

int main(void) {
    pcg32_random_t rng;
    pcg32_srandom_r(&rng, 42u, 54u);

    const uint32_t actual = pcg32_random_r(&rng);
    const uint32_t expected = UINT32_C(0xa15c02b7);
    if (actual != expected) {
        fprintf(stderr, "pcg32_random_r() returned 0x%08" PRIx32
                        ", expected 0x%08" PRIx32 "\n",
                actual, expected);
        return 1;
    }

    puts("pcg-c consumer test: OK");
    return 0;
}
