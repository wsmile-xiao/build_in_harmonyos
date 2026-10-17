#include <aws/common/common.h>
#include <aws/cal/cal.h>
#include <aws/cal/hash.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (!allocator) {
        fprintf(stderr, "Failed to get default allocator\n");
        return 1;
    }

    /* Initialize aws-c-common and aws-c-cal */
    aws_common_library_init(allocator);
    aws_cal_library_init(allocator);

    /* Create a SHA-256 hash instance */
    struct aws_hash *hash = aws_sha256_new(allocator);
    if (!hash) {
        fprintf(stderr, "Failed to create SHA-256 hash\n");
        aws_cal_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }

    /* Hash the string "hello world" */
    const char *data = "hello world";
    struct aws_byte_cursor input = aws_byte_cursor_from_c_str(data);
    if (aws_hash_update(hash, &input) != AWS_OP_SUCCESS) {
        fprintf(stderr, "Failed to update hash\n");
        aws_hash_destroy(hash);
        aws_cal_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }

    /* Finalize and get the digest */
    uint8_t digest[AWS_SHA256_LEN];
    struct aws_byte_buf output = aws_byte_buf_from_array(digest, sizeof(digest));
    output.len = 0;
    if (aws_hash_finalize(hash, &output, 0) != AWS_OP_SUCCESS) {
        fprintf(stderr, "Failed to finalize hash\n");
        aws_hash_destroy(hash);
        aws_cal_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }

    /* Verify digest length */
    if (output.len != AWS_SHA256_LEN) {
        fprintf(stderr, "Digest length mismatch: expected %d, got %zu\n",
                AWS_SHA256_LEN, output.len);
        aws_hash_destroy(hash);
        aws_cal_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }

    /* Print the digest */
    printf("SHA-256(\"%s\") = ", data);
    for (size_t i = 0; i < output.len; i++) {
        printf("%02x", output.buffer[i]);
    }
    printf("\n");

    /* Expected SHA-256 of "hello world" on this platform:
       b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
       Note: matches system sha256sum and Python hashlib on HarmonyOS aarch64 */
    const uint8_t expected[] = {
        0xb9, 0x4d, 0x27, 0xb9, 0x93, 0x4d, 0x3e, 0x08,
        0xa5, 0x2e, 0x52, 0xd7, 0xda, 0x7d, 0xab, 0xfa,
        0xc4, 0x84, 0xef, 0xe3, 0x7a, 0x53, 0x80, 0xee,
        0x90, 0x88, 0xf7, 0xac, 0xe2, 0xef, 0xcd, 0xe9
    };
    if (memcmp(digest, expected, AWS_SHA256_LEN) != 0) {
        fprintf(stderr, "Digest mismatch!\n");
        aws_hash_destroy(hash);
        aws_cal_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }
    printf("Test aws-c-cal 0.9.15: OK (SHA-256 hash computed and verified)\n");

    aws_hash_destroy(hash);
    aws_cal_library_clean_up();
    aws_common_library_clean_up();

    return 0;
}
