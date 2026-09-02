/* test_package for hedley 15 — consumer-side validation of the hedley
 * macro API. Exercises real hedley macros (version, static assert,
 * branch prediction, cast, concat, stringify, flags, attributes) and
 * returns non-zero on any failed check.
 */
#include <hedley.h>
#include <stdio.h>
#include <string.h>

static int checks = 0;
static int failures = 0;

#define CHECK(cond)                                  \
  do {                                               \
    checks++;                                        \
    if (!(cond)) {                                   \
      failures++;                                    \
      fprintf(stderr, "CHECK failed: %s (line %d)\n", #cond, __LINE__); \
    }                                                \
  } while (0)

HEDLEY_STATIC_ASSERT(sizeof(int) >= 2, "int must be at least 16 bits");

static HEDLEY_CONST int square(int x) { return x * x; }
static HEDLEY_PURE int plus_one(int x) { return x + 1; }

#define FOOBAR 42

int main(void) {
  /* 1: version macro present and correct */
  CHECK(HEDLEY_VERSION == 15);

  /* 2: version encode/decode round-trip */
  CHECK(HEDLEY_VERSION_DECODE_MAJOR(HEDLEY_VERSION_ENCODE(15, 0, 0)) == 15);

  /* 3: branch prediction macros usable in conditions */
  int v = 7;
  if (HEDLEY_LIKELY(v > 0)) {
    CHECK(1);
  } else {
    CHECK(0);
  }

  /* 4: UNLIKELY branch */
  if (HEDLEY_UNLIKELY(v < 0)) {
    CHECK(0);
  } else {
    CHECK(1);
  }

  /* 5: CONST-attributed function */
  CHECK(square(6) == 36);

  /* 6: PURE-attributed function */
  CHECK(plus_one(41) == 42);

  /* 7: STATIC_CAST macro */
  CHECK(HEDLEY_STATIC_CAST(int, 3.0) == 3);

  /* 8: CONCAT macro pastes FOO and BAR into FOOBAR (42) */
  CHECK(HEDLEY_CONCAT(FOO, BAR) == 42);

  /* 9: STRINGIFY macro */
  CHECK(strcmp(HEDLEY_STRINGIFY(hedley), "hedley") == 0);

  /* 10: diagnostic push/pop block compiles and runs */
  HEDLEY_DIAGNOSTIC_PUSH
  HEDLEY_DIAGNOSTIC_POP
  CHECK(1);

  printf("hedley test_package: %d checks, %d failed\n", checks, failures);
  return failures == 0 ? 0 : 1;
}
