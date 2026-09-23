#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "clhash.h"

static int check(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    printf("PASS: %s\n", message);
    return 0;
}

int main(void) {
    int failures = 0;
    void *key = get_random_key_for_clhash(UINT64_C(1), UINT64_C(2));
    const uint64_t known = UINT64_C(0xf56dc687673624d3);
    unsigned char bytes[8] = {'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'};

    failures += check(key != NULL, "key generation returns storage");
    if (key == NULL) {
        return 1;
    }

    failures += check(clhash(key, "abc", 3) == known,
                      "known-answer vector matches");
    failures += check(clhash(key, "abc", 3) == clhash(key, "abc", 3),
                      "same key and input are deterministic");
    failures += check(clhash(key, "abc", 3) != clhash(key, "abd", 3),
                      "different input changes the hash");
    failures += check(clhash(key, "", 0) == 0,
                      "empty input has the documented zero hash");

    {
        uint64_t before = clhash(key, (const char *)bytes, sizeof(bytes));
        bytes[0] ^= 1U;
        failures += check(before != clhash(key, (const char *)bytes, sizeof(bytes)),
                          "flipping one input bit changes the hash");
        bytes[0] ^= 1U;
        failures += check(before == clhash(key, (const char *)bytes, sizeof(bytes)),
                          "restoring the input restores the hash");
    }

    failures += check(CLHASH_VERSION_STRING[0] == '1' &&
                      CLHASH_VERSION_MAJOR == 1 &&
                      CLHASH_VERSION_MINOR == 0 &&
                      CLHASH_VERSION_PATCH == 0,
                      "installed header exposes version 1.0.0");

    free(key);
    if (failures != 0) {
        fprintf(stderr, "clhash consumer test failed: %d checks\n", failures);
        return 1;
    }
    printf("clhash consumer test: all 8 checks passed\n");
    return 0;
}
