#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libcanlock-3/canlock.h>

#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

#define CHECK(condition, message) \
    do { \
        if (!(condition)) { \
            fprintf(stderr, "FAIL: %s\n", message); \
            return __LINE__; \
        } \
    } while (0)

int main(void)
{
    static const unsigned char secret[] = "HarmonyOS-PC-secret";
    static const unsigned char message[] = "<canlock-ohos@localhost>";
    unsigned char sensitive[] = "erase-me";
    char *key = cl_get_key(CL_SHA512, secret, sizeof(secret) - 1,
                           message, sizeof(message) - 1);
    char *lock = cl_get_lock(CL_SHA512, secret, sizeof(secret) - 1,
                             message, sizeof(message) - 1);
    size_t index;
    int clear_result;

    CHECK(key != NULL, "SHA-512 Cancel-Key generation works on OHOS musl");
    CHECK(lock != NULL, "SHA-512 Cancel-Lock generation works on OHOS musl");
    CHECK(strncmp(key, "sha512:", 7) == 0, "OHOS key uses the SHA-512 scheme");
    CHECK(strncmp(lock, "sha512:", 7) == 0, "OHOS lock uses the SHA-512 scheme");
    CHECK(cl_verify(CL_SHA512, key + 7, lock + 7) == 0,
          "OHOS-generated SHA-512 pair verifies");

    clear_result = cl_clear_secret(sensitive, sizeof(sensitive), sizeof(sensitive));
    CHECK(clear_result == 0 || clear_result == 1,
          "OHOS provides a supported secret-clearing implementation");
    for (index = 0; index < sizeof(sensitive); ++index) {
        CHECK(sensitive[index] == 0, "secret buffer is zeroed on OHOS");
    }

    free(lock);
    free(key);
    puts("PASS: HarmonyOS canlock SHA-512 and secret clearing");
    return 0;
}
