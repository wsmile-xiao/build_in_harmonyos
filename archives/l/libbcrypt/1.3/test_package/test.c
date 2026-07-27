#include <stdio.h>
#include <string.h>
#include "ow-crypt.h"

int main(void) {
    /* Test crypt_rn: bcrypt hash generation */
    const char *key = "testpassword";
    const char *setting = "$2a$10$usesomesillystringfore";
    char output[64];
    char *result = crypt_rn(key, setting, output, sizeof(output));
    if (result == NULL) {
        fprintf(stderr, "FAIL: crypt_rn returned NULL\n");
        return 1;
    }
    /* Verify the hash starts with $2a$ (bcrypt prefix) */
    if (strncmp(result, "$2a$", 4) != 0) {
        fprintf(stderr, "FAIL: hash does not start with $2a$\n");
        return 1;
    }

    /* Test crypt_gensalt_rn: salt generation */
    char salt[64];
    char *salt_result = crypt_gensalt_rn("$2a$", 10,
        "012345678901234567890123456789", 30,
        salt, sizeof(salt));
    if (salt_result == NULL) {
        fprintf(stderr, "FAIL: crypt_gensalt_rn returned NULL\n");
        return 1;
    }
    /* Verify the salt starts with $2a$ */
    if (strncmp(salt_result, "$2a$", 4) != 0) {
        fprintf(stderr, "FAIL: salt does not start with $2a$\n");
        return 1;
    }

    printf("OK: libbcrypt test passed\n");
    return 0;
}
