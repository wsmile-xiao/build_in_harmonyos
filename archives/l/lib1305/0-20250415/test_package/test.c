// test_package for lib1305 0-20250415 — consumer-side API contract test.
//
// Contract source: upstream doc (https://lib1305.cr.yp.to/api.html) plus the
// configure-generated lib1305.h naming (lib1305_<op>[_<prim>] aliases):
//   - poly1305 authenticator:  lib1305_onetimeauth(a, m, mlen, k)
//     (alias of lib1305_onetimeauth_poly1305), a = 16 bytes, k = 32 bytes.
//   - verification:            lib1305_onetimeauth_verify(a, m, mlen, k)
//     returns 0 when valid, nonzero otherwise.
//   - size macros:             lib1305_onetimeauth_BYTES == 16,
//                              lib1305_onetimeauth_KEYBYTES == 32.
//   - lib1305_version is the release tag ("20250415"), lib1305_arch is the
//     configure-detected architecture ("arm64" on OHOS aarch64), and
//     lib1305_onetimeauth_implementation() names the selected backend.
//
// Known-answer vector: RFC 8439 Section 2.5.2 example and test vector
// (byte-exact transcription of the RFC text, so a broken build cannot
// self-confirm against upstream's embedded SUPERCOP checksums):
//   key = 85d6be78...4149f51b (32 bytes, given directly as the one-time
//   Poly1305 key -- no ChaCha derivation involved),
//   message = "Cryptographic Forum Research Group" (34 bytes),
//   expected tag = a8061dc1305136c6c22b8baf0c0127a9.
// NOTE: Section 2.5.2 is the standalone one-time Poly1305 example
// ("Poly1305 Example and Test Vector"). It is NOT the AEAD construction
// of Section 2.8 / Appendix A.5 (different derived key, AAD + ciphertext
// input). It is used instead of Appendix A.3 #4 because the A.3 #4 key
// bytes (1c9240a5...) are reused across A.2/A.4/A.5 and were repeatedly
// misread as an AEAD vector; this single-block vector is unambiguous.
//
// What is deliberately NOT asserted: benchmark numbers, which backend gets
// selected (runtime decides), and exact cycle behavior.

#include <stdio.h>
#include <string.h>

#include <lib1305.h>

static void print_hex(const char *label, const unsigned char *p, unsigned n)
{
    unsigned i;
    printf("%s:", label);
    for (i = 0; i < n; i++) printf("%02x", p[i]);
    printf("\n");
}

#define CHECK(cond, name, fmt, args...) do {                        \
    int _ok = (cond) ? 1 : 0;                                       \
    printf("[%s] %s: " fmt "\n", _ok ? "PASS" : "FAIL", name, ##args); \
    if (!_ok) ret = 1;                                              \
    checks++;                                                       \
    if (_ok) passed++;                                              \
} while (0)

int main(void)
{
    int ret = 0;
    int checks = 0;
    int passed = 0;

    /* 1. version string matches the adapted upstream release */
    CHECK(strcmp(lib1305_version, "20250415") == 0, "version",
          "lib1305_version() == \"20250415\" (got \"%s\")", lib1305_version);

    /* 2. configure-detected architecture on OHOS aarch64 */
    CHECK(strcmp(lib1305_arch, "arm64") == 0, "arch",
          "lib1305_arch == \"arm64\" (got \"%s\")", lib1305_arch);

    /* 3. a backend was selected at build time */
    {
        const char *impl = lib1305_onetimeauth_implementation();
        CHECK(impl != 0 && impl[0] != '\0', "implementation-nonnull",
              "implementation = \"%s\"", impl ? impl : "(NULL)");
    }

    /* RFC 8439 Section 2.5.2 example and test vector */
    static const unsigned char key[32] = {
        0x85, 0xd6, 0xbe, 0x78, 0x57, 0x55, 0x6d, 0x33,
        0x7f, 0x44, 0x52, 0xfe, 0x42, 0xd5, 0x06, 0xa8,
        0x01, 0x03, 0x80, 0x8a, 0xfb, 0x0d, 0xb2, 0xfd,
        0x4a, 0xbf, 0xf6, 0xaf, 0x41, 0x49, 0xf5, 0x1b
    };
    /* Exact bytes of the RFC text (34-byte message, no newlines);
     * msg-len must print 34. */
    static const unsigned char msg[] =
        "Cryptographic Forum Research Group";
    static const unsigned char expected[16] = {
        0xa8, 0x06, 0x1d, 0xc1, 0x30, 0x51, 0x36, 0xc6,
        0xc2, 0x2b, 0x8b, 0xaf, 0x0c, 0x01, 0x27, 0xa9
    };
    unsigned char a[16];
    unsigned char a2[16];

    /* 4. authenticator matches the RFC vector (canonical entry point) */
    printf("msg-len=%u\n", (unsigned)(sizeof(msg) - 1));
    lib1305_onetimeauth_poly1305(a, msg, (long long)(sizeof(msg) - 1), key);
    print_hex("computed-tag", a, 16);
    print_hex("expected-tag", expected, 16);
    CHECK(memcmp(a, expected, 16) == 0, "rfc8439-kat",
          "poly1305 authenticator matches RFC 8439 Section 2.5.2 example");

    /* 5. short alias and canonical name agree */
    lib1305_onetimeauth(a2, msg, (long long)(sizeof(msg) - 1), key);
    CHECK(memcmp(a, a2, 16) == 0, "alias-agreement",
          "lib1305_onetimeauth == lib1305_onetimeauth_poly1305");

    /* 6. a correct authenticator verifies */
    {
        int rc_ok = lib1305_onetimeauth_verify(expected, msg,
              (long long)(sizeof(msg) - 1), key);
        printf("verify-ok rc=%d\n", rc_ok);
        CHECK(rc_ok == 0, "verify-ok",
              "verify of the RFC vector returns 0 (rc=%d)", rc_ok);
    }

    /* 7. a tampered authenticator must NOT verify (would-be stub detector:
     * a verify() that always returns 0 fails here) */
    {
        unsigned char bad[16];
        int rc_bad;
        memcpy(bad, expected, 16);
        bad[0] ^= 0x01;
        rc_bad = lib1305_onetimeauth_verify(bad, msg,
              (long long)(sizeof(msg) - 1), key);
        printf("verify-tampered rc=%d\n", rc_bad);
        CHECK(rc_bad != 0, "verify-tampered",
              "verify of a 1-bit-tampered tag returns nonzero (rc=%d)", rc_bad);
    }

    /* 8. roundtrip on a different message, and its tag differs */
    {
        static const unsigned char msg2[] = "hello harmonyos";
        unsigned char b[16];
        int rc_rt;
        lib1305_onetimeauth(b, msg2, (long long)(sizeof(msg2) - 1), key);
        rc_rt = lib1305_onetimeauth_verify(b, msg2,
              (long long)(sizeof(msg2) - 1), key);
        printf("roundtrip rc=%d\n", rc_rt);
        print_hex("roundtrip-tag", b, 16);
        CHECK(rc_rt == 0 &&
              memcmp(b, expected, 16) != 0, "roundtrip",
              "auth+verify roundtrip succeeds with a distinct tag (rc=%d)", rc_rt);
    }

    printf("test lib1305 API: %s (%d/%d checks passed)\n",
           ret ? "FAIL" : "OK", passed, checks);
    return ret;
}
