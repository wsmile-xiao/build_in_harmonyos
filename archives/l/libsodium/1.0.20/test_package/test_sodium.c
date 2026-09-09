#include <sodium.h>

#include <stdio.h>
#include <string.h>

static int fail(const char *message)
{
    fprintf(stderr, "libsodium consumer test failed: %s\n", message);
    return 1;
}

int main(void)
{
    static const unsigned char message[] = "HarmonyOS libsodium 1.0.20";
    unsigned char key[crypto_secretbox_KEYBYTES];
    unsigned char nonce[crypto_secretbox_NONCEBYTES];
    unsigned char ciphertext[crypto_secretbox_MACBYTES + sizeof message];
    unsigned char plaintext[sizeof message];
    size_t i;

    if (sodium_init() < 0) {
        return fail("sodium_init returned an error");
    }
    if (strcmp(sodium_version_string(), "1.0.20") != 0) {
        return fail("unexpected library version");
    }

    randombytes_buf(key, sizeof key);
    randombytes_buf(nonce, sizeof nonce);
    if (crypto_secretbox_easy(ciphertext, message, sizeof message, nonce, key) != 0) {
        return fail("crypto_secretbox_easy returned an error");
    }
    if (crypto_secretbox_open_easy(
            plaintext, ciphertext, sizeof ciphertext, nonce, key) != 0) {
        return fail("crypto_secretbox_open_easy rejected valid ciphertext");
    }
    if (memcmp(plaintext, message, sizeof message) != 0) {
        return fail("secretbox round trip changed the plaintext");
    }

    ciphertext[0] ^= 1U;
    if (crypto_secretbox_open_easy(
            plaintext, ciphertext, sizeof ciphertext, nonce, key) == 0) {
        return fail("tampered ciphertext was accepted");
    }

    sodium_memzero(key, sizeof key);
    for (i = 0; i < sizeof key; ++i) {
        if (key[i] != 0U) {
            return fail("sodium_memzero did not clear the key");
        }
    }

    puts("libsodium 1.0.20 consumer test passed");
    return 0;
}
