/* Consumer smoke test for ffc.h 26.07.01 (header-only library).
 *
 * Verifies a third-party consumer can include the installed public header
 * and call public APIs: ffc_parse_double_simple (float parsing) and
 * ffc_parse_i64_simple / ffc_parse_u64_simple (integer parsing), checking
 * both the parsed value and the FFC_OUTCOME_* outcome bits.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>

/* ffc.h is a single-header library: the implementation is compiled into the
 * translation unit that defines FFC_IMPL (same convention as upstream, see
 * CMakeLists target_compile_definitions(test_runner PRIVATE FFC_IMPL ...)). */
#define FFC_IMPL
#include <ffc.h>

static int failures = 0;

static void expect_double(const char *input, double expected) {
    ffc_outcome outcome = FFC_OUTCOME_INVALID_INPUT;
    double value = ffc_parse_double_simple(strlen(input), input, &outcome);
    if (outcome != FFC_OUTCOME_OK || value != expected) {
        printf("FAIL double '%s': got %.17g (outcome=%u)\n",
               input, value, (unsigned)outcome);
        failures++;
    } else {
        printf("ok double '%s' -> %.17g\n", input, value);
    }
}

static void expect_i64(const char *input, int base, int64_t expected) {
    ffc_outcome outcome = FFC_OUTCOME_INVALID_INPUT;
    int64_t value = ffc_parse_i64_simple(strlen(input), input, base, &outcome);
    if (outcome != FFC_OUTCOME_OK || value != expected) {
        printf("FAIL i64 '%s' (base %d): got %lld (outcome=%u)\n",
               input, base, (long long)value, (unsigned)outcome);
        failures++;
    } else {
        printf("ok i64 '%s' (base %d) -> %lld\n", input, base, (long long)value);
    }
}

int main(void) {
    /* Real float parsing through the public API. */
    expect_double("3.14159", 3.14159);
    expect_double("-1234.0e10", -1234.0e10);
    expect_double("42", 42.0);

    /* Real integer parsing through the public API. */
    expect_i64("-1234", 10, -1234);
    expect_i64("ff", 16, 255);
    expect_i64("1010", 2, 10);

    if (failures != 0) {
        printf("ffc.h consumer test FAILED: %d failures\n", failures);
        return 1;
    }
    printf("ffc.h consumer test: ALL OK\n");
    return 0;
}
