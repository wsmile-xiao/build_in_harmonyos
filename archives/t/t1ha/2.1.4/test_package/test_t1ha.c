/*
 * Consumer-side API test for t1ha 2.1.4.
 *
 * Exercises the packaged library from a Conan consumer perspective:
 *   1. upstream self-check vectors for every enabled hash function
 *      (t1ha_selfcheck__all_enabled, returns 0 on success);
 *   2. cross-platform known-answer vectors generated with the pristine
 *      upstream sources on aarch64 macOS (clang) on 2026-09-09;
 *   3. streaming API consistency: t1ha2_init/update/final over a split
 *      buffer must reproduce the single-part streaming result (t1ha2
 *      stream is a distinct algorithm from t1ha2_atonce128);
 *   4. basic determinism and seed sensitivity properties.
 *   5. HarmonyOS target verification: this executable must be compiled for
 *      the OHOS target, so a host-only consumer result cannot be presented as
 *      HarmonyOS validation.
 * Every check aborts (returns non-zero) on failure.
 */
#include <stdio.h>
#include <string.h>
#include <t1ha.h>

static int failures = 0;

static void check(int condition, const char *caption) {
  if (condition) {
    printf("ok - %s\n", caption);
  } else {
    printf("FAILED - %s\n", caption);
    failures++;
  }
}

static void check_value(const char *caption, uint64_t actual,
                        uint64_t expected) {
  if (actual == expected) {
    printf("ok - %s (%016llx)\n", caption, (unsigned long long)actual);
  } else {
    printf("FAILED - %s: got %016llx, expected %016llx\n", caption,
           (unsigned long long)actual, (unsigned long long)expected);
    failures++;
  }
}

int main(void) {
  static const char message[] = "HarmonyOS PC t1ha consumer vector";
  const size_t message_len = sizeof(message) - 1;

  /* 0. This is intentionally target-specific: it verifies the consumer was
   * built for HarmonyOS before exercising the portable t1ha implementation. */
#if defined(__OHOS__)
  check(1, "HarmonyOS native consumer target (__OHOS__)");
#else
  check(0, "HarmonyOS native consumer target (__OHOS__)");
#endif

  /* 1. upstream self-check vectors, all enabled functions */
  check(t1ha_selfcheck__all_enabled() == 0, "t1ha_selfcheck__all_enabled");

  /* 2. known-answer vectors (pristine upstream build, aarch64 macOS) */
  check_value("t1ha2_atonce consumer vector",
              t1ha2_atonce(message, message_len, 42),
              UINT64_C(0xce2fa2e81f8bcdc1));
  check_value("t1ha2_atonce empty input", t1ha2_atonce("", 0, 42),
              UINT64_C(0xbfaaa0c37e075afe));
  check_value("t1ha2_atonce single byte", t1ha2_atonce("a", 1, 42),
              UINT64_C(0xdf4f9a5f4f686f42));
  check_value("t1ha1_le consumer vector",
              t1ha1_le(message, message_len, 42),
              UINT64_C(0xe85ce95b18cdc70e));
  check_value("t1ha0_32le consumer vector",
              t1ha0_32le(message, message_len, 42),
              UINT64_C(0xd6ac83348f21cb58));

  /* 3. streaming API: two-part update must reproduce the single-part
   * result of the same streaming algorithm (t1ha2 stream is a different
   * algorithm from t1ha2_atonce128; init/update/final is its only entry) */
  t1ha_context_t ctx;
  t1ha2_init(&ctx, 42, 42);
  t1ha2_update(&ctx, message, message_len);
  uint64_t single_high = 0;
  const uint64_t single_low = t1ha2_final(&ctx, &single_high);
  t1ha2_init(&ctx, 42, 42);
  t1ha2_update(&ctx, message, 10);
  t1ha2_update(&ctx, message + 10, message_len - 10);
  uint64_t split_high = 0;
  const uint64_t split_low = t1ha2_final(&ctx, &split_high);
  check_value("t1ha2 stream low matches single-part update", split_low,
              single_low);
  check_value("t1ha2 stream high matches single-part update", split_high,
              single_high);
  check(single_low == UINT64_C(0xb9ef42bfdc7ea2d4) &&
            single_high == UINT64_C(0xce8a5c239b05ea34),
        "t1ha2 stream 128-bit known answer");

  /* 4. determinism and seed sensitivity */
  check(t1ha2_atonce(message, message_len, 42) ==
            t1ha2_atonce(message, message_len, 42),
        "same input and seed give the same hash");
  check(t1ha2_atonce(message, message_len, 42) !=
            t1ha2_atonce(message, message_len, 43),
        "different seeds give different hashes");

  if (failures != 0) {
    printf("%d check(s) FAILED\n", failures);
    return 1;
  }
  printf("all t1ha consumer checks passed\n");
  return 0;
}
