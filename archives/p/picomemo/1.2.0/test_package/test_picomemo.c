/*
 * Consumer test for picomemo 1.2.0: compile against the installed headers and
 * link against the installed libpicomemo.so, then drive the public OMEMO 0.3
 * API (store setup, serialization round-trip, signed-prekey rotation and a
 * message encrypt/decrypt round-trip).
 *
 * The shared library is built from the pre-split gen/omemo0.c + gen/omemo2.c,
 * so the exported OMEMO 0.3 entry points carry the `omemo0` prefix and are
 * declared by `gen/omemo0.h`.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "gen/omemo0.h"

static int fails = 0;

#define CK(expr)                                                              \
  do {                                                                        \
    if (expr) {                                                               \
      printf("OK: %s\n", #expr);                                              \
    } else {                                                                  \
      printf("FAIL: %s\n", #expr);                                            \
      fails++;                                                                \
    }                                                                         \
  } while (0)

static int DeterministicRandom(void *p, size_t n) {
  unsigned char *b = (unsigned char *)p;
  for (size_t i = 0; i < n; i++)
    b[i] = (unsigned char)(i * 7 + 3);
  return 0;
}

static int LoadMessageKey(struct omemo0Session *s, struct omemo0MessageKey *k) {
  (void)s;
  (void)k;
  return 1;
}

static int StoreMessageKey(struct omemo0Session *s,
                           const struct omemo0MessageKey *k, uint64_t n) {
  (void)s;
  (void)k;
  (void)n;
  return 0;
}

int main(void) {
  omemo0SetCallbacks(LoadMessageKey, StoreMessageKey, DeterministicRandom);

  struct omemo0Store a, b;
  CK(omemo0SetupStore(&a) == 0);
  CK(omemo0SetupStore(&b) == 0);

  size_t n = omemo0GetSerializedStoreSize(&a);
  CK(n > 0);
  uint8_t *buf = (uint8_t *)malloc(n);
  CK(buf != NULL);
  omemo0SerializeStore(buf, &a);
  memset(&b, 0, sizeof(b));
  CK(omemo0DeserializeStore(buf, n, &b) == 0);
  CK(memcmp(&a, &b, sizeof(a)) == 0);

  CK(omemo0RotateSignedPreKey(&a) == 0);

  const uint8_t *msg = (const uint8_t *)"Hello picomemo!";
  size_t mn = strlen((const char *)msg);
  uint8_t enc[128], key[OMEMO0_KEYSIZE], iv[12], dec[128];
  CK(omemo0EncryptMessage(enc, key, iv, msg, mn) == 0);
  CK(omemo0DecryptMessage(dec, key, OMEMO0_KEYSIZE, iv, enc, mn) == 0);
  CK(memcmp(dec, msg, mn) == 0);

  free(buf);
  printf("PICOMEMO_CONSUMER_FAILS=%d\n", fails);
  return fails ? 1 : 0;
}
