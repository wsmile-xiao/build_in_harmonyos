/*
 * test_harmonyos.c — libb64 2.0.0 HarmonyOS-specific functional test
 *
 * R02 required evidence key: harmonyos_specific_test.
 *
 * This test is compiled and run with the OpenHarmony toolchain
 * (/data/service/hnp/bin/clang, clang 15.0.4). It actually calls the public
 * libb64 2.0.0 C API and validates concrete behaviors:
 *   - encode "Hello, libb64!" -> "SGVsbG8sIGxpYmI2NCE=" (exact Base64)
 *   - encode_length / decode_maxlength helper consistency
 *   - padded decode returns EXACTLY the plaintext length, byte-exact
 *     (2.0.0 fixes the 1.2.1 +1 spurious trailing byte)
 *   - streaming (multi-call) decode is byte-exact
 *
 * It also prints the OHOS compiler identity macros so the log proves the
 * binary was built by the OpenHarmony toolchain rather than the host gcc.
 */
#include <b64/cencode.h>
#include <b64/cdecode.h>

#include <stdio.h>
#include <string.h>

static const char *PLAINTEXT = "Hello, libb64!";
static const char *EXPECTED_B64 = "SGVsbG8sIGxpYmI2NCE=";

int main(void)
{
    int failures = 0;
    size_t ptlen = strlen(PLAINTEXT);
    char enc[128];
    char *c = enc;
    size_t cnt;

    /* ---- Toolchain identity (proves OHOS build, not host gcc) ---- */
#ifdef __clang__
    printf("compiler: clang %d.%d.%d (__clang__ defined)\n",
           __clang_major__, __clang_minor__, __clang_patchlevel__);
#else
    printf("compiler: NOT clang\n");
#endif
#ifdef __aarch64__
    printf("arch: __aarch64__ defined\n");
#endif
#if defined(__OHOS__) || defined(__OHOS)
    printf("platform: OHOS macro defined\n");
#endif
    printf("BASE64_VER_MAJOR=%d BASE64_VER_MINOR=%d\n",
           BASE64_VER_MAJOR, BASE64_VER_MINOR);

    /* ---- Encode ---- */
    base64_encodestate es;
    base64_init_encodestate(&es);
    cnt = base64_encode_block(PLAINTEXT, ptlen, c, &es);
    c += cnt;
    cnt = base64_encode_blockend(c, &es);
    c += cnt;
    *c = 0;

    if (strcmp(enc, EXPECTED_B64) != 0) {
        fprintf(stderr, "[fail] encode mismatch: '%s' vs '%s'\n", enc, EXPECTED_B64);
        failures++;
    } else {
        printf("[ok] encode -> %s\n", enc);
    }

    /* ---- Helpers ---- */
    {
        size_t el = base64_encode_length(ptlen, &es);
        size_t dl = base64_decode_maxlength(strlen(EXPECTED_B64));
        printf("encode_length(%zu)=%zu  decode_maxlength(%zu)=%zu\n",
               ptlen, el, strlen(EXPECTED_B64), dl);
        if (el != strlen(EXPECTED_B64)) {
            fprintf(stderr, "[fail] encode_length\n");
            failures++;
        }
        if (dl < ptlen) {
            fprintf(stderr, "[fail] decode_maxlength too small\n");
            failures++;
        }
    }

    /* ---- Padded one-shot decode ---- */
    {
        char dec[128] = {0};
        base64_decodestate ds;
        base64_init_decodestate(&ds);
        cnt = base64_decode_block(EXPECTED_B64, strlen(EXPECTED_B64), dec, &ds);
        printf("padded decode cnt=%zu (ptlen=%zu)\n", cnt, ptlen);
        if (cnt != ptlen || memcmp(dec, PLAINTEXT, ptlen) != 0) {
            fprintf(stderr, "[fail] padded decode not exact\n");
            failures++;
        } else {
            printf("[ok] padded decode byte-exact (2.0.0 fix)\n");
        }
    }

    /* ---- Streaming decode ---- */
    {
        char dec[128] = {0};
        base64_decodestate ds;
        size_t total = 0;
        const char *p = EXPECTED_B64;
        base64_init_decodestate(&ds);
        while (*p) {
            size_t k = strlen(p);
            if (k > 7) k = 7;
            total += base64_decode_block(p, k, dec + total, &ds);
            p += k;
        }
        printf("streaming total=%zu\n", total);
        if (total != ptlen || memcmp(dec, PLAINTEXT, ptlen) != 0) {
            fprintf(stderr, "[fail] streaming decode not exact\n");
            failures++;
        } else {
            printf("[ok] streaming decode byte-exact\n");
        }
    }

    if (failures) {
        fprintf(stderr, "=== %d FAILED ===\n", failures);
        return 1;
    }
    printf("=== harmonyos_specific_test PASSED ===\n");
    return 0;
}
