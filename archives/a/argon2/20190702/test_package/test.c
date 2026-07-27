#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <argon2.h>

int main(void)
{
    /* Test: Argon2id hash encoded (recommended variant) */
    uint32_t t_cost = 2;
    uint32_t m_cost = 16;
    uint32_t parallelism = 1;
    const char *pwd = "password";
    const char *salt = "somesalt";
    char encoded[128];
    int rc;

    rc = argon2id_hash_encoded(t_cost, m_cost, parallelism,
                                pwd, strlen(pwd),
                                salt, strlen(salt),
                                32, encoded, sizeof(encoded));
    if (rc != ARGON2_OK) {
        fprintf(stderr, "argon2id_hash_encoded failed: %d (%s)\n", rc, argon2_error_message(rc));
        return 1;
    }
    printf("argon2id encoded: %s\n", encoded);

    /* Verify the encoded hash matches the password */
    rc = argon2id_verify(encoded, pwd, strlen(pwd));
    if (rc != ARGON2_OK) {
        fprintf(stderr, "argon2id_verify failed: %d (%s)\n", rc, argon2_error_message(rc));
        return 1;
    }
    printf("argon2id verify: OK\n");

    /* Test: Argon2i raw hash */
    uint8_t hash[32];
    rc = argon2i_hash_raw(t_cost, m_cost, parallelism,
                           pwd, strlen(pwd),
                           salt, strlen(salt),
                           hash, sizeof(hash));
    if (rc != ARGON2_OK) {
        fprintf(stderr, "argon2i_hash_raw failed: %d (%s)\n", rc, argon2_error_message(rc));
        return 1;
    }
    printf("argon2i raw hash: OK (first byte = 0x%02x)\n", hash[0]);

    /* Test: Argon2d encoded hash */
    rc = argon2d_hash_encoded(t_cost, m_cost, parallelism,
                                pwd, strlen(pwd),
                                salt, strlen(salt),
                                32, encoded, sizeof(encoded));
    if (rc != ARGON2_OK) {
        fprintf(stderr, "argon2d_hash_encoded failed: %d (%s)\n", rc, argon2_error_message(rc));
        return 1;
    }
    printf("argon2d encoded: %s\n", encoded);

    printf("All argon2 tests passed!\n");
    return 0;
}
