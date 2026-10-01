/* Fuzzer driver — feeds deterministic pseudo-random inputs to the upstream
 * LLVMFuzzerTestOneInput entry (test/fuzzer.cpp, unmodified). Runs the
 * malloc-failure injection path without libFuzzer, which the OHOS clang
 * toolchain does not ship. Any crash / sanitizer abort fails the test. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);

int main(void) {
    unsigned int seed = 20260929u;
    size_t sizes[] = {16, 31, 64, 128, 256, 1024, 4096};
    for (size_t k = 0; k < sizeof(sizes) / sizeof(sizes[0]); ++k) {
        size_t n = sizes[k];
        uint8_t *buf = (uint8_t *)malloc(n);
        if (!buf)
            return 1;
        for (size_t i = 0; i < n; ++i) {
            seed = seed * 1103515245u + 12345u;
            buf[i] = (uint8_t)(seed >> 16);
        }
        int rc = LLVMFuzzerTestOneInput(buf, n);
        free(buf);
        if (rc != 0) {
            printf("fuzzer driver: input %zu rc=%d\n", n, rc);
            return 1;
        }
    }
    printf("fuzzer driver: %zu deterministic inputs OK\n",
           sizeof(sizes) / sizeof(sizes[0]));
    return 0;
}
