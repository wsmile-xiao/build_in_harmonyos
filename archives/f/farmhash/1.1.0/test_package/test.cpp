/* test_farmhash — HarmonyOS consumer test for farmhash 1.1.0
 * Verifies the installed libfarmhash API against upstream-known vectors
 * (computed from the official google/farmhash v1.1 source, commit 34c13dd).
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <farmhash.h>

int main(void) {
  const char* s = "hello";
  size_t n = strlen(s);
  int rc = 0;

  /* Known vectors from the conan Release build (NDEBUG: DebugTweak off).
   * aarch64: can_use_sse41=0 -> Hash32==farmhashmk::Hash32,
   * len<=64: Hash64==farmhashxo->farmhashna==Fingerprint64. */
  if (util::Hash64(s, n) != 13009744463427800296ULL) {
    fprintf(stderr, "FAIL Hash64\n");
    rc = 1;
  }
  if (util::Hash64WithSeed(s, n, 1234) != 5697833563375938151ULL) {
    fprintf(stderr, "FAIL Hash64WithSeed\n");
    rc = 1;
  }
  if (util::Hash32(s, n) != 2039911270U) {
    fprintf(stderr, "FAIL Hash32\n");
    rc = 1;
  }
  if (util::Fingerprint64(s, n) != 13009744463427800296ULL) {
    fprintf(stderr, "FAIL Fingerprint64\n");
    rc = 1;
  }
  if (util::Fingerprint32(s, n) != 2039911270U) {
    fprintf(stderr, "FAIL Fingerprint32\n");
    rc = 1;
  }
  if (util::Hash64(s, 0) != 11160318154034397263ULL) {
    fprintf(stderr, "FAIL Hash64(empty)\n");
    rc = 1;
  }

  if (rc == 0) {
    printf("test_farmhash: all 6 vectors PASS\n");
  }
  return rc;
}