#include <stdio.h>
#include <string.h>

#include "rhash.h"

static int check_digest(unsigned hash_id, const char *input, const char *expected)
{
    unsigned char result[64];
    char hex[129];
    size_t digest_size;

    if (rhash_msg(hash_id, input, strlen(input), result) != 0) {
        return 1;
    }
    digest_size = rhash_get_digest_size(hash_id);
    rhash_print_bytes(hex, result, digest_size, RHPR_HEX);
    return strcmp(hex, expected) != 0;
}

int main(void)
{
    rhash_library_init();

    if (rhash_count() < 30) {
        fprintf(stderr, "FAIL: expected at least 30 hash algorithms, got %d\n", rhash_count());
        return 1;
    }
    if (check_digest(RHASH_MD5, "hello", "5d41402abc4b2a76b9719d911017c592") != 0) {
        fprintf(stderr, "FAIL: MD5 mismatch\n");
        return 2;
    }
    if (check_digest(RHASH_SHA1, "message digest", "c12252ceda8be8994d5fa0290a47231c1d16aae3") != 0) {
        fprintf(stderr, "FAIL: SHA1 mismatch\n");
        return 3;
    }
    printf("PASS: MD5/SHA1 API checks\n");
    return 0;
}
