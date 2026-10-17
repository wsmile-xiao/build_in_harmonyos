#include <mceliece.h>
#include <stdio.h>
#include <string.h>
int main(void) {
    static unsigned char pk[mceliece348864_PUBLICKEYBYTES];
    static unsigned char sk[mceliece348864_SECRETKEYBYTES];
    static unsigned char ct[mceliece348864_CIPHERTEXTBYTES];
    unsigned char k1[mceliece348864_BYTES];
    unsigned char k2[mceliece348864_BYTES];
    mceliece348864_keypair(pk, sk);
    if (mceliece348864_enc(ct, k1, pk) != 0) {
        fprintf(stderr, "enc failed\n");
        return 1;
    }
    if (mceliece348864_dec(k2, ct, sk) != 0) {
        fprintf(stderr, "dec failed\n");
        return 1;
    }
    if (memcmp(k1, k2, mceliece348864_BYTES) != 0) {
        fprintf(stderr, "kem mismatch\n");
        return 1;
    }
    printf("mceliece348864 kem ok impl=%s\n", mceliece_kem_348864_implementation());
    return 0;
}
