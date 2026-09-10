/* test_package consumer for CBQN's public FFI header (include/bqnffi.h).
 *
 * It drives the *installed* package: initialise the embedded interpreter, evaluate real BQN
 * programs, hand arrays built in C to BQN functions and check the values that come back.
 * Any mismatch exits non-zero, so ctest (and therefore conan create / CI) really fails.
 */
#include <bqnffi.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks;
static int failures;

static void check_int(const char *what, long got, long want)
{
    ++checks;
    if (got != want) {
        ++failures;
        printf("FAIL %-34s got %ld want %ld\n", what, got, want);
    } else {
        printf("ok   %-34s = %ld\n", what, got);
    }
}

static void check_real(const char *what, double got, double want)
{
    ++checks;
    if (!(fabs(got - want) < 1e-12)) {
        ++failures;
        printf("FAIL %-34s got %.17g want %.17g\n", what, got, want);
    } else {
        printf("ok   %-34s = %.17g\n", what, got);
    }
}

static void check_true(const char *what, int cond)
{
    ++checks;
    if (!cond) {
        ++failures;
        printf("FAIL %s\n", what);
    } else {
        printf("ok   %s\n", what);
    }
}

int main(void)
{
    bqn_init();

    /* 1. plain arithmetic through the embedded interpreter */
    check_real("2+2", bqn_toF64(bqn_evalCStr("2+2")), 4.0);

    /* 2. fold over a BQN list: +\u00b4\u27e81,2,3,4\u27e9 = 10 */
    check_real("+\u00b4\u27e81,2,3,4\u27e9", bqn_toF64(bqn_evalCStr("+\u00b4\u27e81,2,3,4\u27e9")), 10.0);

    /* 3. \u2195 (Range) built by BQN, then the C-side shape queries */
    BQNV rng = bqn_evalCStr("\u2195 6");
    check_int("\u2262 (\u2195 6)", (long)bqn_bound(rng), 6);
    check_int("\u2260 (\u2195 6)", (long)bqn_rank(rng), 1);
    check_real("last element of \u2195 6", bqn_toF64(bqn_pick(rng, 5)), 5.0);
    double raw[6] = {0, 0, 0, 0, 0, 0};
    bqn_readF64Arr(rng, raw);
    check_true("readF64Arr round-trips \u2195 6",
               raw[0] == 0.0 && raw[3] == 3.0 && raw[5] == 5.0);
    bqn_free(rng);

    /* 4. hand a C-built 2x3 array to the interpreter and read it back */
    double data[6] = {0.0, 1.0, 2.0, 3.0, 4.0, 5.0};
    size_t shape[2] = {2, 3};
    BQNV arr = bqn_makeF64Arr(2, shape, data);
    check_int("bound of C-made 2\u203f3 array", (long)bqn_bound(arr), 6);
    check_int("rank of C-made 2\u203f3 array", (long)bqn_rank(arr), 2);
    size_t got_shape[2] = {0, 0};
    bqn_shape(arr, got_shape);
    check_int("shape[0]", (long)got_shape[0], 2);
    check_int("shape[1]", (long)got_shape[1], 3);
    check_real("element 4 of C-made array", bqn_toF64(bqn_pick(arr, 4)), 4.0);
    bqn_free(arr);

    /* 5. reduce a C-built vector with a BQN function value (bqn_call1) */
    double small[4] = {1.0, 2.0, 3.0, 4.0};
    BQNV vec = bqn_makeF64Vec(4, small);
    BQNV fold = bqn_evalCStr("+\u00b4");
    check_real("+\u00b4 of C-made vector", bqn_toF64(bqn_call1(fold, vec)), 10.0);
    bqn_free(vec);

    /* 6. dyadic call from C: 3 + 4 */
    BQNV three = bqn_makeF64(3.0);
    BQNV four = bqn_makeF64(4.0);
    BQNV plus = bqn_evalCStr("+");
    check_real("3 + 4 (bqn_call2)", bqn_toF64(bqn_call2(plus, three, four)), 7.0);
    bqn_free(plus);

    /* 7. \u234b (Grade Up) on \u27e83,1,2\u27e9 gives the permutation \u27e81,2,0\u27e9 */
    BQNV grade = bqn_evalCStr("\u234b \u27e83,1,2\u27e9");
    check_int("first index of grade-up", (long)bqn_toF64(bqn_pick(grade, 0)), 1);
    check_int("second index of grade-up", (long)bqn_toF64(bqn_pick(grade, 1)), 2);
    check_int("third index of grade-up", (long)bqn_toF64(bqn_pick(grade, 2)), 0);

    /* 8. UTF-8 strings: length counts code points, not bytes */
    const char *ascii = "abcde";
    BQNV str = bqn_makeUTF8Str(strlen(ascii), ascii);
    check_int("length of \"abcde\"", (long)bqn_bound(str), 5);
    bqn_free(str);
    /* the same text with one 2-byte UTF-8 code point must still count as 5 characters.  The
     * array is written with explicit (char) casts so no compiler may reinterpret the escapes:
     * bytes are h, 0xC3, 0xA9, l, l, o = 6 bytes -> "héllo" = 5 code points.  The assertion is
     * discriminating: a byte-wise count, or escapes degraded to ASCII '3'/'9', both give 6. */
    static const char utf8[] = {'h', (char)0xc3, (char)0xa9, 'l', 'l', 'o'};
    BQNV accented = bqn_makeUTF8Str(sizeof utf8 / sizeof *utf8, utf8);
    check_int("length of h+U+00E9+llo (6 bytes)", (long)bqn_bound(accented), 5);
    bqn_free(accented);

    /* 9. boundary + type discrimination */
    BQNV empty = bqn_evalCStr("\u27e8\u27e9");
    BQNV one = bqn_evalCStr("1");
    check_int("bound of \u27e8\u27e9", (long)bqn_bound(empty), 0);
    check_true("\u2022Type distinguishes array from number", bqn_type(empty) != bqn_type(one));
    check_true("\u2022Type is stable for the same object", bqn_type(one) == bqn_type(one));

    printf("\n%d checks, %d failures\n", checks, failures);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
