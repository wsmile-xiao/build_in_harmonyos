#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <isa-l.h>

/* 6 real consumer assertions against the installed libisal. Vectors for
 * checks 1-2 are upstream's own known answers (crc/crc_simple_test.c):
 * 48 bytes 0..47, crc16_t10dif(0x1234) = 0x60b3,
 * crc32_ieee(0x12345678) = 0x2ceadbe3. */

#define CHECK(n, cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "check %d FAILED: %s (line %d)\n", n, #cond, __LINE__); \
        return 10 + (n); \
    } \
    printf("check %d ok\n", n); \
} while (0)

#define EC_K 4
#define EC_P 2
#define EC_LEN 128

static unsigned char *ec_alloc(void) {
    void *p = NULL;
    if (posix_memalign(&p, 64, EC_LEN) != 0 || p == NULL) {
        fprintf(stderr, "posix_memalign failed\n");
        exit(20);
    }
    return (unsigned char *) p;
}

int main(void) {
    unsigned char buf[48];
    int i;

    for (i = 0; i < 48; i++)
        buf[i] = (unsigned char) i;

    /* 1-2: fixed known-answer CRC vectors (non-empty, exact match). */
    CHECK(1, crc16_t10dif(0x1234, buf, 48) == 0x60b3);
    CHECK(2, crc32_ieee(0x12345678, buf, 48) == 0x2ceadbe3);

    /* 3: CRC chaining is self-consistent over a split buffer. */
    {
        uint32_t half = crc32_ieee(0, buf, 24);
        uint32_t full = crc32_ieee(0, buf, 48);
        uint32_t chained = crc32_ieee(half, buf + 24, 24);
        CHECK(3, chained == full);
    }

    /* 4: installed library reports its own version. */
    CHECK(4, isal_get_version() == ISAL_MAKE_VERSION(2, 32, 1));
    printf("libisal version: %s\n", isal_get_version_str());

    /* 5-6: erasure coding is linear (zero in -> zero parity) and
     * deterministic + non-degenerate on real data (catches zero-stubs). */
    {
        unsigned char matrix[EC_K * EC_P];
        unsigned char gftbls[EC_K * EC_P * 32];
        unsigned char *data[EC_K];
        unsigned char *par[EC_P];
        unsigned char *par2[EC_P];
        int k, p, allzero, same, nonzero;

        for (i = 0; i < EC_K * EC_P; i++)
            matrix[i] = (unsigned char) (i + 1);
        for (k = 0; k < EC_K; k++)
            data[k] = ec_alloc();
        for (p = 0; p < EC_P; p++) {
            par[p] = ec_alloc();
            par2[p] = ec_alloc();
        }

        ec_init_tables(EC_K, EC_P, matrix, gftbls);

        for (k = 0; k < EC_K; k++)
            memset(data[k], 0, EC_LEN);
        for (p = 0; p < EC_P; p++)
            memset(par[p], 0xA5, EC_LEN);
        ec_encode_data(EC_LEN, EC_K, EC_P, gftbls, data, par);
        allzero = 1;
        for (p = 0; p < EC_P && allzero; p++)
            for (i = 0; i < EC_LEN; i++)
                if (par[p][i] != 0) {
                    allzero = 0;
                    break;
                }
        CHECK(5, allzero);

        for (k = 0; k < EC_K; k++)
            for (i = 0; i < EC_LEN; i++)
                data[k][i] = (unsigned char) ((k * 31 + i * 7 + 1) & 0xFF);
        ec_encode_data(EC_LEN, EC_K, EC_P, gftbls, data, par);
        ec_encode_data(EC_LEN, EC_K, EC_P, gftbls, data, par2);
        same = 1;
        nonzero = 0;
        for (p = 0; p < EC_P; p++)
            for (i = 0; i < EC_LEN; i++) {
                if (par[p][i] != par2[p][i])
                    same = 0;
                if (par[p][i] != 0)
                    nonzero = 1;
            }
        CHECK(6, same && nonzero);

        for (k = 0; k < EC_K; k++)
            free(data[k]);
        for (p = 0; p < EC_P; p++) {
            free(par[p]);
            free(par2[p]);
        }
    }

    printf("isal API assertions: 6 passed\n");
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,"
           "\"command\":\"./test_isal\",\"discovered\":6,\"passedCount\":6}\n");
    return 0;
}
