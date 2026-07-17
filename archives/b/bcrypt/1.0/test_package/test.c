#include <stdio.h>
#include <string.h>
#include "bcrypt.h"

int main(void) {
    char salt[BCRYPT_HASHSIZE];
    char hash[BCRYPT_HASHSIZE];
    char password[] = "test123";

    /* Generate salt with work factor 4 (fast for testing) */
    if (bcrypt_gensalt(4, salt) != 0) {
        fprintf(stderr, "FAIL: bcrypt_gensalt failed\n");
        return 1;
    }
    printf("Generated salt: %s\n", salt);

    /* Hash the password */
    if (bcrypt_hashpw(password, salt, hash) != 0) {
        fprintf(stderr, "FAIL: bcrypt_hashpw failed\n");
        return 1;
    }
    printf("Hashed password: %s\n", hash);

    /* Verify the password matches the hash */
    if (bcrypt_checkpw(password, hash) != 0) {
        fprintf(stderr, "FAIL: bcrypt_checkpw should match\n");
        return 1;
    }
    printf("Password check: OK\n");

    /* Verify wrong password is rejected */
    if (bcrypt_checkpw("wrongpass", hash) == 0) {
        fprintf(stderr, "FAIL: bcrypt_checkpw should reject wrong password\n");
        return 1;
    }
    printf("Wrong password rejected: OK\n");

    printf("All tests passed!\n");
    return 0;
}
