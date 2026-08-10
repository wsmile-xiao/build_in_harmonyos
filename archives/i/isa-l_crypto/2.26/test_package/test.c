#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <isa-l_crypto/md5_mb.h>

/* MD5("abc") = 900150983cd24fb0d6963f7d28e17f72 */
static const uint8_t expected_md5[16] = {
    0x90, 0x01, 0x50, 0x98, 0x3c, 0xd2, 0x4f, 0xb0,
    0xd6, 0x96, 0x3f, 0x7d, 0x28, 0xe1, 0x7f, 0x72
};

int main(void) {
    ISAL_MD5_HASH_CTX_MGR mgr;
    ISAL_MD5_HASH_CTX ctx;
    ISAL_MD5_HASH_CTX *ctx_out = NULL;
    const char *msg = "abc";

    /* Initialize context manager and context */
    isal_md5_ctx_mgr_init(&mgr);
    isal_hash_ctx_init(&ctx);

    /* Submit "abc" as a complete message (FIRST | LAST) */
    isal_md5_ctx_mgr_submit(&mgr, &ctx, &ctx_out, (const void *)msg, 3,
                            ISAL_HASH_FIRST | ISAL_HASH_LAST);

    /* Flush to get result if not already returned */
    if (ctx_out == NULL) {
        isal_md5_ctx_mgr_flush(&mgr, &ctx_out);
    }

    if (ctx_out == NULL) {
        fprintf(stderr, "ERROR: no context returned after flush\n");
        return 1;
    }

    /* Compare digest */
    uint8_t *digest = (uint8_t *)ctx_out->job.result_digest;
    if (memcmp(digest, expected_md5, 16) != 0) {
        fprintf(stderr, "ERROR: MD5 digest mismatch\n");
        fprintf(stderr, "  got:      ");
        for (int i = 0; i < 16; i++) fprintf(stderr, "%02x", digest[i]);
        fprintf(stderr, "\n  expected: 900150983cd24fb0d6963f7d28e17f72\n");
        return 1;
    }

    printf("isa-l_crypto MD5 test: PASS\n");
    printf("MD5(\"abc\") = ");
    for (int i = 0; i < 16; i++) printf("%02x", digest[i]);
    printf("\n");
    return 0;
}
