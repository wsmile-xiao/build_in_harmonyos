#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <huffman/huffman.h>

/* R34: test_package 必须实质调用被测库 API —— 内存编解码往返验证 */
int main(void)
{
    const unsigned char input[] =
        "huffman 1.2.7 round-trip test: the quick brown fox jumps over the lazy dog 0123456789";
    unsigned char *encoded = NULL, *decoded = NULL;
    uint32_t encoded_len = 0, decoded_len = 0;
    int rc = 0;

    if (huffman_encode_memory(input, (uint32_t)(sizeof(input) - 1),
                              &encoded, &encoded_len) != 0) {
        fprintf(stderr, "huffman_encode_memory failed\n");
        rc = 1;
        goto out;
    }
    if (encoded == NULL || encoded_len == 0) {
        fprintf(stderr, "encode produced no output\n");
        rc = 1;
        goto out;
    }
    if (huffman_decode_memory(encoded, encoded_len,
                              &decoded, &decoded_len) != 0) {
        fprintf(stderr, "huffman_decode_memory failed\n");
        rc = 1;
        goto out;
    }
    if (decoded_len != sizeof(input) - 1 ||
        memcmp(decoded, input, decoded_len) != 0) {
        fprintf(stderr, "round-trip mismatch: got %u bytes, expected %zu\n",
                decoded_len, sizeof(input) - 1);
        rc = 1;
        goto out;
    }

    printf("huffman round-trip OK: %zu -> %u -> %u bytes\n",
           sizeof(input) - 1, encoded_len, decoded_len);

out:
    free(encoded);
    free(decoded);
    return rc;
}
