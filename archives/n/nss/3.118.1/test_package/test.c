#include <stdio.h>
#include <string.h>

#include "nss.h"
#include "secoid.h"
#include "pk11pub.h"
#include "sechash.h"
#include "sslproto.h"

/* Consumer smoke test for NSS 3.118.1 (L1).
 *
 * Verifies that the packaged NSS actually initializes and performs crypto:
 *   1. NSS_NoDB_Init()  -> real NSS runtime init (loads softoken/freebl)
 *   2. HASH_HashBuf()   -> SHA-256 against the NIST "abc" test vector
 *   3. NSS_GetVersion() -> compiled-in version string == "3.118.1"
 *   4. SEC_OID_* constants are exposed by the packaged headers (compile-time)
 */
int main(void) {
    /* 1. Real NSS initialization (no cert/key database) */
    if (NSS_NoDB_Init(NULL) != SECSuccess) {
        fprintf(stderr, "FAIL: NSS_NoDB_Init error=%d\n", PORT_GetError());
        return 1;
    }

    /* 2. SHA-256 of "abc" must match the NIST vector
     *    ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad */
    static const unsigned char expect[32] = {
        0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,
        0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad };
    unsigned char digest[32];
    unsigned int digest_len = 0;
    if (HASH_HashBuf(HASH_AlgSHA256, digest, (const unsigned char *)"abc", 3) != SECSuccess) {
        fprintf(stderr, "FAIL: HASH_HashBuf(SHA256) error=%d\n", PORT_GetError());
        return 1;
    }
    if (digest_len != 0) { /* HASH_HashBuf ignores digest_len on input */ }
    if (memcmp(digest, expect, 32) != 0) {
        fprintf(stderr, "FAIL: SHA-256('abc') mismatch\n");
        return 1;
    }

    /* 3. Version assertion */
    const char *ver = NSS_GetVersion();
    printf("NSS version: %s\n", ver ? ver : "(null)");
    if (ver == NULL || strncmp(ver, "3.118.1", 7) != 0) {
        fprintf(stderr, "FAIL: unexpected NSS version '%s'\n", ver ? ver : "(null)");
        return 1;
    }

    /* 4. Compile-time OID sanity */
    if (SEC_OID_SHA256 <= SEC_OID_UNKNOWN || SEC_OID_AES_256_CBC <= SEC_OID_UNKNOWN) {
        fprintf(stderr, "FAIL: SEC_OID constants invalid\n");
        return 1;
    }

    printf("test nss 3.118.1: OK\n");
    return 0;
}
