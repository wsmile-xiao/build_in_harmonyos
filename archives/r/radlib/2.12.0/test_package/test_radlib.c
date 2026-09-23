/*
 * radlib consumer test (test_package).
 *
 * Compiles against the packaged public headers (h/*.h) and links the
 * packaged radlib, then exercises the exported crypto API with hard
 * assertions:
 *   - radSHA1ComputeBlock / radSHA256ComputeBlock against the FIPS 180
 *     test vectors (SHA-1("abc"), SHA-1(""), SHA-256("abc")). The upstream
 *     SHA implementation assumed 32-bit words but used unsigned long,
 *     which is 64-bit on LP64/aarch64 (garbled digests + SIGBUS); recipe
 *     patches 0001/0003 fix this and the vectors below prove it.
 *   - radCRC32Calculate / radCRC16Calculate against values computed by
 *     replicating radlib's exact table-driven loops (src/radcrc.c):
 *     CRC-32("123456789") = 0x340BC6D9 (standard reflected table, seed
 *     0xFFFFFFFF, radlib omits the final XOR), CRC-16("123456789") = 0x6F91.
 *
 * Exit code 0 = every assertion passed; nonzero = at least one failure.
 */
#include <stdio.h>
#include <string.h>

#include "radcrc.h"
#include "radsha.h"

static int failures = 0;

static void check(int cond, const char *what)
{
    if (cond) {
        printf("PASS: %s\n", what);
    } else {
        printf("FAIL: %s\n", what);
        failures++;
    }
}

int main(void)
{
    char digest1[RADSHA1_DIGEST_STR_LENGTH];
    char digest256[RADSHA256_DIGEST_STR_LENGTH];

    /* 1) SHA-1 memory block, FIPS 180-1 test vector */
    memset(digest1, 0, sizeof(digest1));
    if (radSHA1ComputeBlock((void *)"abc", 3, digest1) != OK) {
        printf("FAIL: radSHA1ComputeBlock returned an error\n");
        failures++;
    } else {
        printf("INFO: SHA1('abc') = %s\n", digest1);
        check(strcmp(digest1, "a9993e364706816aba3e25717850c26c9cd0d89d") == 0,
              "SHA1('abc') matches the FIPS 180-1 test vector");
    }

    /* 2) SHA-1 empty input edge case, FIPS vector */
    memset(digest1, 0, sizeof(digest1));
    if (radSHA1ComputeBlock((void *)"", 0, digest1) != OK) {
        printf("FAIL: radSHA1ComputeBlock(empty) returned an error\n");
        failures++;
    } else {
        printf("INFO: SHA1('') = %s\n", digest1);
        check(strcmp(digest1, "da39a3ee5e6b4b0d3255bfef95601890afd80709") == 0,
              "SHA1('') matches the FIPS empty-input test vector");
    }

    /* 3) SHA-256 memory block, FIPS 180-4 test vector */
    memset(digest256, 0, sizeof(digest256));
    if (radSHA256ComputeBlock((void *)"abc", 3, digest256) != OK) {
        printf("FAIL: radSHA256ComputeBlock returned an error\n");
        failures++;
    } else {
        printf("INFO: SHA256('abc') = %s\n", digest256);
        check(strcmp(digest256, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") == 0,
              "SHA256('abc') matches the FIPS 180-4 test vector");
    }

    /* 4) CRC-32 over the standard check string */
    ULONG crc32 = radCRC32Calculate((void *)"123456789", 9);
    printf("INFO: CRC32('123456789') = 0x%08lX\n", (unsigned long)crc32);
    check(crc32 == 0x340BC6D9UL, "CRC32('123456789') == 0x340BC6D9 (radlib table/seed, no final xor)");

    /* 5) CRC-16 over the standard check string */
    USHORT crc16 = radCRC16Calculate((void *)"123456789", 9);
    printf("INFO: CRC16('123456789') = 0x%04X\n", (unsigned)crc16);
    check(crc16 == 0x6F91, "CRC16('123456789') == 0x6F91 (radlib table/seed)");

    /* 6) CRC-32 empty input edge case must not corrupt the running CRC */
    ULONG crc32_empty = radCRC32Calculate((void *)"", 0);
    printf("INFO: CRC32('') = 0x%08lX\n", (unsigned long)crc32_empty);
    check(crc32_empty == 0xFFFFFFFFUL, "CRC32('') == seed 0xFFFFFFFF (no bytes consumed)");

    if (failures == 0) {
        printf("ALL TESTS PASSED\n");
        return 0;
    }
    printf("%d TEST(S) FAILED\n", failures);
    return 1;
}
