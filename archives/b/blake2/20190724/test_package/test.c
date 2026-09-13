#include "blake2.h"
#include <stdio.h>
#include <string.h>

/* Official BLAKE2 test vectors — empty input digests
 * blake2b-256("") = 0e5751c026e543b2e8ab2eb06099daa1d1e5df47778f7787faab45cdf12fe3a8
 * blake2s-256("") = 69217a3079908094e11121d042354a7c1f55b6482ca1a51e1b250dfd1ed0eef9
 */
int main(void) {
    unsigned char out[32];
    const char *msg = "";

    if (blake2b(out, 32, msg, 0, NULL, 0) != 0) {
        fprintf(stderr, "blake2b() failed\n");
        return 1;
    }
    const unsigned char exp_b[32] = {
        0x0e,0x57,0x51,0xc0,0x26,0xe5,0x43,0xb2,0xe8,0xab,0x2e,0xb0,0x60,0x99,0xda,0xa1,
        0xd1,0xe5,0xdf,0x47,0x77,0x8f,0x77,0x87,0xfa,0xab,0x45,0xcd,0xf1,0x2f,0xe3,0xa8
    };
    if (memcmp(out, exp_b, 32) != 0) {
        fprintf(stderr, "blake2b empty-input digest mismatch\n");
        return 1;
    }
    printf("blake2b empty-input ok\n");

    if (blake2s(out, 32, msg, 0, NULL, 0) != 0) {
        fprintf(stderr, "blake2s() failed\n");
        return 1;
    }
    const unsigned char exp_s[32] = {
        0x69,0x21,0x7a,0x30,0x79,0x90,0x80,0x94,0xe1,0x11,0x21,0xd0,0x42,0x35,0x4a,0x7c,
        0x1f,0x55,0xb6,0x48,0x2c,0xa1,0xa5,0x1e,0x1b,0x25,0x0d,0xfd,0x1e,0xd0,0xee,0xf9
    };
    if (memcmp(out, exp_s, 32) != 0) {
        fprintf(stderr, "blake2s empty-input digest mismatch\n");
        return 1;
    }
    printf("blake2s empty-input ok\n");

    printf("blake2 test_package PASSED\n");
    return 0;
}