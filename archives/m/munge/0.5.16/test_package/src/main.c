#include <stdio.h>
#include <munge.h>

int main(void) {
    int valid = munge_enum_is_valid(MUNGE_ENUM_CIPHER, MUNGE_CIPHER_AES256);
    if (!valid) {
        fprintf(stderr, "FAIL: MUNGE_CIPHER_AES256 should be valid\n");
        return 1;
    }

    const char *str = munge_enum_int_to_str(MUNGE_ENUM_CIPHER, MUNGE_CIPHER_AES256);
    if (!str) {
        fprintf(stderr, "FAIL: munge_enum_int_to_str returned NULL\n");
        return 1;
    }
    printf("Cipher AES256 name: %s\n", str);

    const char *errstr = munge_strerror(EMUNGE_SUCCESS);
    if (!errstr) {
        fprintf(stderr, "FAIL: munge_strerror returned NULL\n");
        return 1;
    }
    printf("Success error string: %s\n", errstr);

    int val = munge_enum_str_to_int(MUNGE_ENUM_MAC, "SHA256");
    if (val != MUNGE_MAC_SHA256) {
        fprintf(stderr, "FAIL: munge_enum_str_to_int returned %d\n", val);
        return 1;
    }

    printf("All munge tests passed!\n");
    return 0;
}
