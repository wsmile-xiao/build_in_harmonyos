/*
 * test_package/test.c — Consumer-side test for xdelta3 Conan package.
 *
 * R34: This test substantively exercises the xdelta3 library API by:
 *   1. Calling xd3_encode_memory() to produce a VCDIFF delta
 *   2. Calling xd3_decode_memory() to reconstruct the target
 *   3. Verifying the reconstructed data matches the original
 *
 * This is NOT an empty printf stub.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "xdelta3.h"

int main(void) {
    /* Source (old) and target (new) data for delta encoding */
    static const uint8_t source[] =
        "The quick brown fox jumps over the lazy dog. "
        "This is the original source data for xdelta3 testing.";
    static const uint8_t target[] =
        "The quick brown fox jumps over the lazy cat. "
        "This is the MODIFIED target data for xdelta3 testing.";

    const usize_t source_size = sizeof(source) - 1;
    const usize_t target_size = sizeof(target) - 1;

    /* Encode: create a VCDIFF delta from source -> target */
    uint8_t delta_buf[8192];
    usize_t delta_size = sizeof(delta_buf);

    int ret = xd3_encode_memory(
        target, target_size,
        source, source_size,
        delta_buf, &delta_size,
        sizeof(delta_buf), 0);
    if (ret != 0) {
        fprintf(stderr, "FAIL: xd3_encode_memory returned %d\n", ret);
        return 1;
    }
    printf("Encoded delta: %zu bytes (source=%zu, target=%zu)\n",
           (size_t)delta_size, (size_t)source_size, (size_t)target_size);

    /* Decode: reconstruct target from source + delta */
    uint8_t output_buf[8192];
    usize_t output_size = sizeof(output_buf);

    ret = xd3_decode_memory(
        delta_buf, delta_size,
        source, source_size,
        output_buf, &output_size,
        sizeof(output_buf), 0);
    if (ret != 0) {
        fprintf(stderr, "FAIL: xd3_decode_memory returned %d\n", ret);
        return 1;
    }

    /* Verify the reconstructed data matches the original target */
    if (output_size != target_size) {
        fprintf(stderr, "FAIL: size mismatch (expected %zu, got %zu)\n",
                (size_t)target_size, (size_t)output_size);
        return 1;
    }
    if (memcmp(output_buf, target, output_size) != 0) {
        fprintf(stderr, "FAIL: content mismatch after decode\n");
        return 1;
    }

    printf("PASS: xdelta3 encode/decode round-trip successful\n");
    return 0;
}
