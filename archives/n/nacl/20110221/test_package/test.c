/* Consumer checks for nacl/20110221 as delivered by this recipe.
 *
 * Two kinds of assertions:
 *   - known-answer tests for sha256/sha512/poly1305 whose expected values were
 *     computed independently (CPython hashlib plus a 12-line Poly1305), so they prove
 *     the OHOS aarch64 codegen is byte-correct rather than merely self-consistent;
 *   - protocol round trips with tamper/wrong-key rejection, plus x25519 agreement and
 *     cpucycles/randombytes resolution through the packaged archive, which is what
 *     proves the two in-tree objects folded in package() are actually usable by a
 *     consumer that only links -lnacl.
 *
 * Argument shapes follow upstream's own tests/ programs. Public Domain.
 */
#include <stdio.h>
#include <string.h>

#include "crypto_hash.h"
#include "crypto_hash_sha256.h"
#include "crypto_hash_sha512.h"
#include "crypto_onetimeauth.h"
#include "crypto_verify_16.h"
#include "crypto_auth.h"
#include "crypto_auth_hmacsha512256.h"
#include "crypto_secretbox.h"
#include "crypto_box.h"
#include "crypto_scalarmult_curve25519.h"
#include "crypto_sign.h"
#include "crypto_stream.h"
#include "randombytes.h"
#include "cpucycles.h"

#define MSG "testing\n"
#define MSGLEN 8

static int checks;
static int failures;

#define CHECK(cond)                                                          \
  do {                                                                       \
    ++checks;                                                                \
    if (!(cond)) {                                                           \
      ++failures;                                                            \
      printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);                 \
    }                                                                        \
  } while (0)

static void hexdump(char *out, const unsigned char *in, size_t len)
{
  size_t i;
  for (i = 0; i < len; ++i)
    sprintf(out + 2 * i, "%02x", (unsigned int) in[i]);
  out[2 * len] = 0;
}

static void check_hex(const unsigned char *digest, size_t len, const char *want,
                      const char *what)
{
  char got[2 * 64 + 1];
  hexdump(got, digest, len);
  CHECK(strcmp(got, want) == 0);
  if (strcmp(got, want) != 0)
    printf("  %s\n    got  %s\n    want %s\n", what, got, want);
}

int main(void)
{
  static unsigned char big[768];
  unsigned char d[64], d2[64], key[32], nonce[24];
  unsigned char m[64], c[64], m2[64];
  char hex[2 * 64 + 1];
  size_t i;
  unsigned long long smlen, mlen;

  for (i = 0; i < sizeof key; ++i)
    key[i] = (unsigned char) i;
  for (i = 0; i < sizeof big; ++i)
    big[i] = (unsigned char) (i & 0xff);
  memset(nonce, 0, sizeof nonce);

  /* --- hash: known answers from hashlib, and the selected-primitive dispatch --- */
  CHECK(crypto_hash_sha256_BYTES == 32);
  CHECK(crypto_hash_sha512_BYTES == 64);
  CHECK(crypto_hash_BYTES == 64);
  crypto_hash_sha256(d, (const unsigned char *) MSG, MSGLEN);
  check_hex(d, 32, "12a61f4e173fb3a11c05d6471f74728f76231b4a5fcd9667cef3af87a3ae4dc2", "sha256(msg)");
  crypto_hash_sha512(d, (const unsigned char *) MSG, MSGLEN);
  check_hex(d, 64, "24f950aac7b9ea9b3cb728228a0c82b67c39e96b4b344798870d5daee93e3ae5"
                   "931baae8c7cacfea4b629452c38026a81d138bc7aad1af3ef7bfd5ec646d6c28", "sha512(msg)");
  crypto_hash_sha256(d, big, sizeof big);
  check_hex(d, 32, "f3a25aa93aa2fbba28d79260535bbd6a5eb0fc1c24a8b0f04e12b484c1dfe363", "sha256(768B)");
  crypto_hash_sha512(d, big, sizeof big);
  check_hex(d, 64, "f1721f49518ee462a3d81def26d81037cd474b4254b85ad7c8f1509594d0177b"
                   "bb996ee9625813852bacac108c2a72c83a8587050fec1dcda64730d6470953e6", "sha512(768B)");
  memset(d2, 0, sizeof d2);
  crypto_hash(d, (const unsigned char *) MSG, MSGLEN);
  CHECK(memcmp(d, d2, 64) != 0); /* d2 untouched: sanity on the comparison itself */
  crypto_hash(d2, (const unsigned char *) MSG, MSGLEN);
  CHECK(memcmp(d, d2, 64) == 0);
  crypto_hash_sha512(d2, (const unsigned char *) MSG, MSGLEN);
  CHECK(memcmp(d, d2, 64) == 0); /* crypto_hash() must dispatch to sha512 */

  /* --- onetimeauth: known answers from an independent Poly1305 --- */
  CHECK(crypto_onetimeauth_BYTES == 16);
  CHECK(crypto_onetimeauth_KEYBYTES == 32);
  crypto_onetimeauth(d, (const unsigned char *) MSG, MSGLEN, key);
  hexdump(hex, d, 16);
  CHECK(strcmp(hex, "6a340aaed0f5ca4a43505d6a7784919e") == 0);
  crypto_onetimeauth(d, big, sizeof big, key);
  hexdump(hex, d, 16);
  CHECK(strcmp(hex, "960d54a7d96cee67fee2a6e31597b16b") == 0);
  CHECK(crypto_onetimeauth_verify(d, big, sizeof big, key) == 0);
  big[0] ^= 1;
  CHECK(crypto_onetimeauth_verify(d, big, sizeof big, key) != 0);
  big[0] ^= 1;
  CHECK(crypto_verify_16(d, d) == 0);

  /* --- auth: generic header and hmacsha512256 header must agree --- */
  CHECK(crypto_auth_BYTES == 32);
  CHECK(crypto_auth_KEYBYTES == 32);
  crypto_auth(d, (const unsigned char *) MSG, MSGLEN, key);
  crypto_auth_hmacsha512256(d2, (const unsigned char *) MSG, MSGLEN, key);
  CHECK(memcmp(d, d2, 32) == 0);
  CHECK(crypto_auth_verify(d, (const unsigned char *) MSG, MSGLEN, key) == 0);
  d2[0] ^= 1;
  CHECK(crypto_auth_verify(d2, (const unsigned char *) MSG, MSGLEN, key) != 0);
  d2[0] ^= 1;

  /* --- secretbox: round trip, ciphertext differs, tamper rejected --- */
  CHECK(crypto_secretbox_ZEROBYTES == 32);
  CHECK(crypto_secretbox_BOXZEROBYTES == 16);
  memset(m, 0, sizeof m);
  memcpy(m + crypto_secretbox_ZEROBYTES, MSG, MSGLEN);
  memset(c, 0, sizeof c);
  crypto_secretbox(c, m, MSGLEN + crypto_secretbox_ZEROBYTES, nonce, key);
  CHECK(memcmp(c + crypto_secretbox_BOXZEROBYTES, MSG, MSGLEN) != 0);
  memset(m2, 0, sizeof m2);
  CHECK(crypto_secretbox_open(m2, c, MSGLEN + crypto_secretbox_ZEROBYTES, nonce, key) == 0);
  CHECK(memcmp(m2 + crypto_secretbox_ZEROBYTES, MSG, MSGLEN) == 0);
  c[20] ^= 1;
  CHECK(crypto_secretbox_open(m2, c, MSGLEN + crypto_secretbox_ZEROBYTES, nonce, key) != 0);
  c[20] ^= 1;

  /* --- box: both directions plus the beforenm/afternm split API --- */
  {
    unsigned char alicepk[32], alicesk[32], bobpk[32], bobsk[32], k[32];
    crypto_box_keypair(alicepk, alicesk);
    crypto_box_keypair(bobpk, bobsk);
    CHECK(memcmp(alicepk, bobpk, 32) != 0);
    memset(m, 0, sizeof m);
    memcpy(m + crypto_box_ZEROBYTES, MSG, MSGLEN);
    memset(c, 0, sizeof c);
    crypto_box(c, m, MSGLEN + crypto_box_ZEROBYTES, nonce, bobpk, alicesk);
    memset(m2, 0, sizeof m2);
    CHECK(crypto_box_open(m2, c, MSGLEN + crypto_box_ZEROBYTES, nonce, alicepk, bobsk) == 0);
    CHECK(memcmp(m2 + crypto_box_ZEROBYTES, MSG, MSGLEN) == 0);
    memset(m2, 0, sizeof m2);
    /* bobsk with bobpk derives a different shared secret than alicesk with bobpk */
    CHECK(crypto_box_open(m2, c, MSGLEN + crypto_box_ZEROBYTES, nonce, bobpk, bobsk) != 0);
    CHECK(crypto_box_beforenm(k, bobpk, alicesk) == 0);
    memset(c, 0, sizeof c);
    crypto_box_afternm(c, m, MSGLEN + crypto_box_ZEROBYTES, nonce, k);
    CHECK(memcmp(c + crypto_box_BOXZEROBYTES, m + crypto_box_ZEROBYTES, MSGLEN) != 0);
    memset(m2, 0, sizeof m2);
    CHECK(crypto_box_open_afternm(m2, c, MSGLEN + crypto_box_ZEROBYTES, nonce, k) == 0);
    CHECK(memcmp(m2 + crypto_box_ZEROBYTES, MSG, MSGLEN) == 0);
  }

  /* --- scalarmult: x25519 Diffie-Hellman agreement --- */
  {
    unsigned char alicesk[32], alicepk[32], bobsk[32], bobpk[32], s1[32], s2[32];
    for (i = 0; i < 32; ++i)
      alicesk[i] = (unsigned char) (i + 1);
    memset(bobsk, 0, 32);
    bobsk[0] = 5;
    CHECK(crypto_scalarmult_curve25519_base(alicepk, alicesk) == 0);
    CHECK(crypto_scalarmult_curve25519_base(bobpk, bobsk) == 0);
    CHECK(memcmp(alicepk, bobpk, 32) != 0);
    CHECK(crypto_scalarmult_curve25519(s1, alicesk, bobpk) == 0);
    CHECK(crypto_scalarmult_curve25519(s2, bobsk, alicepk) == 0);
    CHECK(memcmp(s1, s2, 32) == 0);
  }

  /* --- sign: keypair, sign, open, tamper --- */
  {
    unsigned char pk[crypto_sign_PUBLICKEYBYTES];
    unsigned char sk[crypto_sign_SECRETKEYBYTES];
    unsigned char sm[MSGLEN + crypto_sign_BYTES + 8];
    CHECK(crypto_sign_keypair(pk, sk) == 0);
    CHECK(crypto_sign(sm, &smlen, (const unsigned char *) MSG, MSGLEN, sk) == 0);
    CHECK(smlen == MSGLEN + crypto_sign_BYTES);
    memset(m2, 0, sizeof m2);
    CHECK(crypto_sign_open(m2, &mlen, sm, smlen, pk) == 0);
    CHECK(mlen == MSGLEN);
    CHECK(memcmp(m2, MSG, MSGLEN) == 0);
    sm[4] ^= 1;
    CHECK(crypto_sign_open(m2, &mlen, sm, smlen, pk) != 0);
    sm[4] ^= 1;
    pk[0] ^= 1;
    CHECK(crypto_sign_open(m2, &mlen, sm, smlen, pk) != 0);
  }

  /* --- stream: deterministic keystream, nonce-sensitive, xor is an involution --- */
  CHECK(crypto_stream_KEYBYTES == 32);
  CHECK(crypto_stream_NONCEBYTES == 24);
  crypto_stream(d, 32, nonce, key);
  crypto_stream(d2, 32, nonce, key);
  CHECK(memcmp(d, d2, 32) == 0);
  nonce[0] ^= 1;
  crypto_stream(d2, 32, nonce, key);
  CHECK(memcmp(d, d2, 32) != 0);
  nonce[0] ^= 1;
  memset(m, 0, sizeof m);
  crypto_stream_xor(c, (const unsigned char *) MSG, MSGLEN, nonce, key);
  crypto_stream_xor(m, c, MSGLEN, nonce, key);
  CHECK(memcmp(m, MSG, MSGLEN) == 0);

  /* --- randombytes and cpucycles: shipped from nacl's own tree, so a consumer
         that only links -lnacl must be able to resolve both --- */
  memset(d, 0, sizeof d);
  memset(d2, 0, sizeof d2);
  randombytes(d, 32);
  randombytes(d2, 32);
  CHECK(memcmp(d, d2, 32) != 0);
  CHECK(strlen(cpucycles_implementation) > 0);
  CHECK(cpucycles_persecond() > 0);
  CHECK(cpucycles() <= cpucycles());

  printf("nacl consumer checks=%d failures=%d\n", checks, failures);
  return failures ? 1 : 0;
}
