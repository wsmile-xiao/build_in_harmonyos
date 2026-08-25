/* Consumer test for libversion 3.0.4
 *
 * Covers the core public API declared in libversion/version.h:
 *   - version_compare2(v1, v2)           basic 2-operand comparison
 *   - version_compare4(v1, v2, f1, f2)   comparison with per-operand flags
 *   - VERSIONFLAG_P_IS_PATCH             flag: treat 'p' suffix as patch
 *   - LIBVERSION_VERSION_ATLEAST(x,y,z)  compile-time version check
 *   - LIBVERSION_VERSION_MAJOR/MINOR/PATCH  version constants from config.h
 *
 * All comparison semantics verified against upstream test suite (compare_test.c)
 * and native build API verification.
 */
#include <stdio.h>
#include <string.h>
#include <libversion/version.h>

static int g_errors = 0;

#define CHECK(expr, fmt, ...) \
    do { \
        if (!(expr)) { \
            fprintf(stderr, "FAIL [%s:%d]: " fmt "\n", __func__, __LINE__, ##__VA_ARGS__); \
            g_errors++; \
        } \
    } while (0)

/* ── Equal versions ─────────────────────────────────────────────── */
static void test_equal(void) {
    CHECK(version_compare2("1.0", "1.0") == 0, "expected 1.0==1.0");
    CHECK(version_compare2("2.3.4", "2.3.4") == 0, "expected 2.3.4==2.3.4");
    CHECK(version_compare2("1.0.0", "1.0") == 0, "expected 1.0.0==1.0 (trailing zeros ignored)");
}

/* ── Greater / less than ────────────────────────────────────────── */
static void test_greater_less(void) {
    CHECK(version_compare2("1.1", "1.0") > 0, "expected 1.1>1.0");
    CHECK(version_compare2("1.0", "1.1") < 0, "expected 1.0<1.1");
    CHECK(version_compare2("2.0", "1.9.9") > 0, "expected 2.0>1.9.9");
    CHECK(version_compare2("1.9.9", "2.0") < 0, "expected 1.9.9<2.0");
}

/* ── Multi-segment versions (numeric, not lexical) ──────────────── */
static void test_multi_segment(void) {
    CHECK(version_compare2("1.2.3", "1.2.4") < 0, "expected 1.2.3<1.2.4");
    CHECK(version_compare2("1.2.4", "1.2.3") > 0, "expected 1.2.4>1.2.3");
    CHECK(version_compare2("1.2.10", "1.2.9") > 0, "expected 1.2.10>1.2.9 (numeric not lexical)");
    CHECK(version_compare2("10.0.0", "9.0.0") > 0, "expected 10.0.0>9.0.0");
}

/* ── Prerelease / special version rules ──────────────────────────── */
/* libversion semantics (verified against upstream compare_test.c):
 *   alpha < beta < pre < rc < (release) < post/pl
 */
static void test_prerelease(void) {
    /* prerelease suffixes sort BEFORE the release */
    CHECK(version_compare2("1.0_alpha", "1.0") < 0, "expected alpha<release");
    CHECK(version_compare2("1.0_alpha", "1.0_beta") < 0, "expected alpha<beta");
    CHECK(version_compare2("1.0_beta", "1.0_pre") < 0, "expected beta<pre");
    CHECK(version_compare2("1.0_pre", "1.0_rc1") < 0, "expected pre<rc1");
    CHECK(version_compare2("1.0_rc1", "1.0") < 0, "expected rc1<release");
    CHECK(version_compare2("1.0_rc1", "1.0_rc2") < 0, "expected rc1<rc2");
    /* post-release / patch-level (pl) sorts AFTER the release */
    CHECK(version_compare2("1.0pl1", "1.0") > 0, "expected pl1>release");
    CHECK(version_compare2("1.0pl1", "1.0pl2") < 0, "expected pl1<pl2");
    CHECK(version_compare2("1.0pl1", "1.1") < 0, "expected pl1<1.1");
    CHECK(version_compare2("1.0", "1.0_alpha") > 0, "expected release>alpha");
}

/* ── version_compare4 with VERSIONFLAG_P_IS_PATCH ───────────────── */
/* By default 'p' is treated as a prerelease marker (1.0p1 < 1.0).
 * With VERSIONFLAG_P_IS_PATCH, 'p' is treated as a patch marker (1.0p1 > 1.0).
 */
static void test_flags(void) {
    /* Default: p is prerelease → 1.0p1 < 1.0 */
    CHECK(version_compare2("1.0p1", "1.0") < 0, "expected 1.0p1<1.0 (default: p as prerelease)");
    /* With flag: p is patch → 1.0p1 > 1.0 */
    CHECK(version_compare4("1.0p1", "1.0", VERSIONFLAG_P_IS_PATCH, 0) > 0,
          "expected 1.0p1>1.0 with VERSIONFLAG_P_IS_PATCH");
}

/* ── LIBVERSION_VERSION_ATLEAST macro ───────────────────────────── */
static void test_version_atleast(void) {
    CHECK(LIBVERSION_VERSION_ATLEAST(3, 0, 4) == 1, "expected ATLEAST(3,0,4)==1");
    CHECK(LIBVERSION_VERSION_ATLEAST(3, 0, 5) == 0, "expected ATLEAST(3,0,5)==0");
    CHECK(LIBVERSION_VERSION_ATLEAST(2, 0, 0) == 1, "expected ATLEAST(2,0,0)==1");
}

/* ── Version constants from config.h ────────────────────────────── */
static void test_version_constants(void) {
    CHECK(LIBVERSION_VERSION_MAJOR == 3, "expected MAJOR==3, got %d", LIBVERSION_VERSION_MAJOR);
    CHECK(LIBVERSION_VERSION_MINOR == 0, "expected MINOR==0, got %d", LIBVERSION_VERSION_MINOR);
    CHECK(LIBVERSION_VERSION_PATCH == 4, "expected PATCH==4, got %d", LIBVERSION_VERSION_PATCH);
}

int main(void) {
    test_equal();
    test_greater_less();
    test_multi_segment();
    test_prerelease();
    test_flags();
    test_version_atleast();
    test_version_constants();

    if (g_errors > 0) {
        fprintf(stderr, "\n*** %d CHECK(s) FAILED ***\n", g_errors);
        return 1;
    }
    printf("All libversion consumer checks passed.\n");
    return 0;
}
