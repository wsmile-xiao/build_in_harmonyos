/* test_blst.c - consumer test for the packaged blst 0.3.17 on HarmonyOS PC.
 *
 * This is a *consumer* test (test_package), NOT an upstream test.  Upstream
 * blst ships no C test program; its own suites live in bindings/go (28 tests)
 * and bindings/rust (23 tests) and are counted separately.
 *
 * What this proves: the packaged libblst.a links and the AArch64 assembly
 * routines inside it compute correctly on the HarmonyOS worker.
 *
 *  T1  hash_to_g1 KAT - RFC 9380 / draft-irtf-cfrg-hash-to-curve
 *      "BLS12381G1_XMD:SHA-256_SSWU_RO_" with the empty message; expected
 *      P.x/P.y taken verbatim from the upstream vector file
 *      bindings/vectors/hash_to_curve/BLS12381G1_XMD_SHA-256_SSWU_RO_.json
 *  T2  keygen -> sk_to_pk_in_g1 -> sign -> verify (positive path)
 *  T3  same signature against a different message must FAIL (negative path)
 *  T4  G1 compression / decompression round-trip
 *  T5  G1 point membership check via blst_p1_affine_on_curve
 */
#include <stdio.h>
#include <string.h>
#include <stdbool.h>

#include "blst.h"

static int failures = 0;
static int checks = 0;

static void check(int cond, const char *name)
{
    checks++;
    if (cond) {
        printf("  PASS  %s\n", name);
    } else {
        printf("  FAIL  %s\n", name);
        failures++;
    }
}

static void hex2bin(const char *hex, unsigned char *out, size_t outlen)
{
    size_t i;
    for (i = 0; i < outlen; i++) {
        unsigned int b;
        sscanf(hex + 2 * i, "%2x", &b);
        out[i] = (unsigned char)b;
    }
}

/* T1 expected values (upstream vector, empty message) */
static const char *VEC_PX =
    "052926add2207b76ca4fa57a8734416c8dc95e24501772c814278700eed6d1e4"
    "e8cf62d9c09db0fac349612b759e79a1";
static const char *VEC_PY =
    "08ba738453bfed09cb546dbb0783dbb3a5f1f566ed67bb6be0e8c67e2e81a4c"
    "c68ee29813bb7994998f3eae0c9c6a265";
static const char *VEC_DST =
    "QUUX-V01-CS02-with-BLS12381G1_XMD:SHA-256_SSWU_RO_";

int main(void)
{
    printf("blst consumer test (packaged library)\n");

    /* ---- T1: hash_to_g1 known-answer test ---------------------------- */
    {
        blst_p1 h;
        blst_p1_affine ha;
        unsigned char px[48], py[48];

        blst_hash_to_g1(&h, (const byte *)"", 0,
                        (const byte *)VEC_DST, strlen(VEC_DST), NULL, 0);
        blst_p1_to_affine(&ha, &h);

        /* blst_fp stores little-endian limbs; convert to big-endian bytes */
        blst_bendian_from_fp(px, &ha.x);
        blst_bendian_from_fp(py, &ha.y);

        check(blst_p1_affine_on_curve(&ha), "T1a hash_to_g1 output is on curve");

        /* compare against the vector, expressed as big-endian hex */
        unsigned char expx[48], expy[48];
        hex2bin(VEC_PX, expx, 48);
        hex2bin(VEC_PY, expy, 48);
        check(memcmp(px, expx, 48) == 0, "T1b hash_to_g1 x matches upstream vector");
        check(memcmp(py, expy, 48) == 0, "T1c hash_to_g1 y matches upstream vector");
    }

    /* ---- T2/T3: keygen, sign, verify --------------------------------- */
    {
        static const byte IKM[] = "harmonyos-pc-blst-consumer-test-ikm";
        static const byte DST[] = "BLS_SIG_BLS12381G2_XMD:SHA-256_SSWU_RO_NUL_";
        static const byte MSG[] = "hello OpenHarmony PC";
        blst_scalar sk;
        blst_p1 pk;
        blst_p2 hash, sig;
        blst_p1_affine pk_aff;
        blst_p2_affine sig_aff;
        BLST_ERROR e1, e2;

        blst_keygen(&sk, IKM, sizeof(IKM) - 1, NULL, 0);
        blst_sk_to_pk_in_g1(&pk, &sk);
        blst_p1_to_affine(&pk_aff, &pk);
        check(blst_p1_affine_on_curve(&pk_aff), "T5  public key is on curve");

        blst_hash_to_g2(&hash, MSG, sizeof(MSG) - 1, DST, sizeof(DST) - 1,
                        NULL, 0);
        blst_sign_pk_in_g1(&sig, &hash, &sk);
        blst_p2_to_affine(&sig_aff, &sig);

        e1 = blst_core_verify_pk_in_g1(&pk_aff, &sig_aff, true,
                                       MSG, sizeof(MSG) - 1,
                                       DST, sizeof(DST) - 1, NULL, 0);
        check(e1 == BLST_SUCCESS, "T2  sign -> verify round-trip succeeds");

        e2 = blst_core_verify_pk_in_g1(&pk_aff, &sig_aff, true,
                                       (const byte *)"tampered message", 16,
                                       DST, sizeof(DST) - 1, NULL, 0);
        check(e2 != BLST_SUCCESS, "T3  tampered message is rejected");
    }

    /* ---- T4: G1 compression round-trip ------------------------------- */
    {
        blst_p1 h;
        blst_p1_affine ha;
        byte comp[48];
        blst_p1_affine back;
        BLST_ERROR e;

        blst_hash_to_g1(&h, (const byte *)"roundtrip", 9,
                        (const byte *)VEC_DST, strlen(VEC_DST), NULL, 0);
        blst_p1_to_affine(&ha, &h);
        blst_p1_affine_compress(comp, &ha);
        e = blst_p1_uncompress(&back, comp);
        {
            byte bx[48], by[48], cx[48], cy[48];
            blst_bendian_from_fp(bx, &ha.x);
            blst_bendian_from_fp(by, &ha.y);
            blst_bendian_from_fp(cx, &back.x);
            blst_bendian_from_fp(cy, &back.y);
            check(e == BLST_SUCCESS &&
                      memcmp(bx, cx, 48) == 0 && memcmp(by, cy, 48) == 0,
                  "T4  G1 compress/uncompress round-trip is lossless");
        }
    }

    printf("\nchecks=%d failures=%d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
