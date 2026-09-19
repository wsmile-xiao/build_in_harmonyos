#include <disorder.h>

#include <math.h>
#include <stdint.h>
#include <stdio.h>

#ifndef __OHOS__
#error "test_ohos must be compiled with the HarmonyOS/OHOS toolchain"
#endif

#ifndef __aarch64__
#error "HarmonyOS PC validation requires the AArch64 target"
#endif

static int checks = 0;

#define CHECK(condition)                                                        \
    do {                                                                        \
        ++checks;                                                               \
        if (!(condition)) {                                                     \
            fprintf(stderr, "OHOS check %d failed: %s\n", checks, #condition); \
            return 1;                                                           \
        }                                                                       \
    } while (0)

int main(void)
{
    unsigned char buffer[4096];
    const uint16_t endian_probe = 1;
    FILE *random_source;
    float entropy;

    CHECK(sizeof(void *) == 8);
    CHECK(*(const unsigned char *)&endian_probe == 1);
    random_source = fopen("/dev/urandom", "rb");
    CHECK(random_source != NULL);
    CHECK(fread(buffer, 1, sizeof(buffer), random_source) == sizeof(buffer));
    CHECK(fclose(random_source) == 0);

    entropy = shannon_H((char *)buffer, sizeof(buffer));
    CHECK(isfinite(entropy) && entropy > 0.0f && entropy <= 8.0f);
    CHECK(get_num_tokens() > 1 && get_num_tokens() <= 256);
    CHECK(isfinite(get_entropy_ratio()) && get_entropy_ratio() > 0.0f
          && get_entropy_ratio() <= 1.000001f);

    printf("HarmonyOS entropy test passed: %d checks, entropy=%.6f\n",
           checks, entropy);
    return 0;
}

