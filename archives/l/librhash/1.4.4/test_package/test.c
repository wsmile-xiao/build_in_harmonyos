#include <stdio.h>
#include <string.h>

#include <rhash.h>

static int check_equal(const char* name, const char* got, const char* expected)
{
    if (strcmp(got, expected) != 0) {
        fprintf(stderr, "%s mismatch: got %s expected %s\n", name, got, expected);
        return 1;
    }
    return 0;
}

int main(void)
{
    const char* message = "message digest";
    unsigned char digest[64];
    char output[130];
    rhash ctx;

    rhash_library_init();

    if (rhash_count() < 31) {
        fprintf(stderr, "unexpected hash count: %d\n", rhash_count());
        return 1;
    }

    if (rhash_get_digest_size(RHASH_SHA1) != 20) {
        fprintf(stderr, "unexpected SHA1 digest size\n");
        return 2;
    }

    if (rhash_msg(RHASH_SHA1, message, strlen(message), digest) != 0) {
        fprintf(stderr, "rhash_msg failed\n");
        return 3;
    }

    rhash_print_bytes(output, digest, rhash_get_digest_size(RHASH_SHA1), RHPR_HEX | RHPR_UPPERCASE);
    if (check_equal("SHA1", output, "C12252CEDA8BE8994D5FA0290A47231C1D16AAE3")) {
        return 4;
    }

    ctx = rhash_init(RHASH_MD5 | RHASH_SHA1);
    if (!ctx) {
        fprintf(stderr, "rhash_init failed\n");
        return 5;
    }

    if (rhash_update(ctx, message, strlen(message)) != 0) {
        fprintf(stderr, "rhash_update failed\n");
        rhash_free(ctx);
        return 6;
    }

    if (rhash_final(ctx, NULL) != 0) {
        fprintf(stderr, "rhash_final failed\n");
        rhash_free(ctx);
        return 7;
    }

    rhash_print(output, ctx, RHASH_MD5, RHPR_HEX | RHPR_UPPERCASE);
    if (check_equal("MD5", output, "F96B697D7CB7938D525A2F31AAF161D0")) {
        rhash_free(ctx);
        return 8;
    }

    rhash_print(output, ctx, RHASH_SHA1, RHPR_HEX | RHPR_UPPERCASE);
    if (check_equal("SHA1 low-level", output, "C12252CEDA8BE8994D5FA0290A47231C1D16AAE3")) {
        rhash_free(ctx);
        return 9;
    }

    rhash_free(ctx);
    return 0;
}
