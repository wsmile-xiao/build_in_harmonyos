#include <libbz3.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Conan L1 official test — must actually exercise the packaged library.
 * Calls the public bzip3 API (bz3_version / bz3_compress / bz3_decompress)
 * and verifies a real round-trip; a print-only shell would violate R34.
 */
int main(void) {
    const char *src = "bzip3 test_package: HarmonyOS conan smoke";
    size_t src_len = strlen(src);
    size_t bound = bz3_bound(src_len);

    uint8_t *comp = (uint8_t *)calloc(1, bound);
    uint8_t *decomp = (uint8_t *)calloc(1, src_len + 64);
    if (!comp || !decomp) {
        fprintf(stderr, "alloc failed\n");
        return 1;
    }

    size_t comp_len = bound;
    int rc = bz3_compress(16, (const uint8_t *)src, comp, src_len, &comp_len);
    if (rc != BZ3_OK) {
        fprintf(stderr, "bz3_compress rc=%d\n", rc);
        return 2;
    }

    size_t decomp_len = src_len + 64;
    rc = bz3_decompress(comp, decomp, comp_len, &decomp_len);
    if (rc != BZ3_OK) {
        fprintf(stderr, "bz3_decompress rc=%d\n", rc);
        return 3;
    }

    if (decomp_len != src_len || memcmp(decomp, src, src_len) != 0) {
        fprintf(stderr, "round-trip mismatch\n");
        return 4;
    }

    printf("bzip3 %s round-trip OK (%zu -> %zu bytes)\n",
           bz3_version(), src_len, comp_len);
    free(comp);
    free(decomp);
    return 0;
}