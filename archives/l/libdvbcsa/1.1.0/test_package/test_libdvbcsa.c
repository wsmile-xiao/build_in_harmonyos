#include <dvbcsa/dvbcsa.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    const dvbcsa_cw_t control_word = {0x01, 0x23, 0x45, 0x67,
                                     0x89, 0xab, 0xcd, 0xef};
    unsigned char payload[184];
    unsigned char original[sizeof payload];
    for (unsigned i = 0; i < sizeof payload; ++i) {
        payload[i] = (unsigned char)(i * 17u + 3u);
    }
    memcpy(original, payload, sizeof payload);

    dvbcsa_key_t *key = dvbcsa_key_alloc();
    if (key == NULL) {
        fputs("dvbcsa_key_alloc failed\n", stderr);
        return 1;
    }
    dvbcsa_key_set(control_word, key);
    dvbcsa_encrypt(key, payload, sizeof payload);
    if (memcmp(payload, original, sizeof payload) == 0) {
        fputs("encryption did not transform payload\n", stderr);
        dvbcsa_key_free(key);
        return 2;
    }
    dvbcsa_decrypt(key, payload, sizeof payload);
    if (memcmp(payload, original, sizeof payload) != 0) {
        fputs("decryption did not restore payload\n", stderr);
        dvbcsa_key_free(key);
        return 3;
    }
    dvbcsa_key_free(key);
    puts("libdvbcsa installed API roundtrip passed");
    return 0;
}
