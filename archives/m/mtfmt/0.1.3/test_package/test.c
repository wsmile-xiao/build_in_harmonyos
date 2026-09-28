// SPDX-License-Identifier: LGPL-3.0
// mtfmt 0.1.3 — consumer test (test_package)
//
// Exercises the *installed* public API of the packaged mtfmt static/shared
// library: format-string evaluation, alignment/fill, integer base styles,
// argument-id handling, parser error codes, the C string helpers and the
// built-in heap allocator's balance invariant.
//
// Expected strings are the ones upstream itself asserts in tests/ (the very
// suite build() runs), so this program cross-checks that the packaged
// artifact behaves like the source tree under test.
//
// Every CHECK() is counted and reported; the process exits non-zero if any
// check fails, and prints `mtfmt consumer: N checks, 0 failures` on success.

#include "mtfmt.h"

#include <stdio.h>
#include <string.h>

#define HEAP_SIZE 4096

static byte_t g_heap[HEAP_SIZE];
static unsigned g_checks;
static unsigned g_failures;

static void check(int cond, const char* what, const char* file, int line)
{
    ++g_checks;
    if (!cond) {
        ++g_failures;
        fprintf(
            stderr, "FAIL %s:%d: %s\n", file, line, what ? what : "check"
        );
    }
}

static void check_str(
    const char* got, const char* want, const char* what, const char* file,
    int line
)
{
    ++g_checks;
    if (got == NULL || strcmp(got, want) != 0) {
        ++g_failures;
        fprintf(
            stderr, "FAIL %s:%d: %s\n     got  : %s\n     want : %s\n", file,
            line, what, got ? got : "(null)", want
        );
    }
}

#define CHECK(cond) check((cond), #cond, __FILE__, __LINE__)
#define CHECK_STR(got, want) \
    check_str((got), (want), #got " == " #want, __FILE__, __LINE__)

// Format `fmt` with the given placeholder count and 0-4 int arguments, and
// compare the produced text with `want`.
static void expect_format(
    const char* fmt, unsigned place, int want_fail, const char* want,
    int a0, int a1, int a2, const char* what
)
{
    MString s;
    mstr_result_t res;

    if (MSTR_SUCC(mstr_create_empty(&s))) {
        res = mstr_format(&s, fmt, (usize_t)place, a0, a1, a2);
        if (want_fail) {
            ++g_checks;
            if (res == MStr_Ok) {
                ++g_failures;
                fprintf(
                    stderr, "FAIL: %s: expected an error, got MStr_Ok\n", what
                );
            }
        } else {
            ++g_checks;
            if (res != MStr_Ok) {
                ++g_failures;
                fprintf(
                    stderr, "FAIL: %s: mstr_format returned %d\n", what,
                    (int)res
                );
            } else {
                check_str(mstr_c_str(&s), want, what, __FILE__, __LINE__);
            }
        }
        mstr_free(&s);
    } else {
        ++g_checks;
        ++g_failures;
        fprintf(stderr, "FAIL: %s: mstr_create_empty failed\n", what);
    }
}

static void expect_format_error(
    const char* fmt, unsigned place, mstr_result_t want, int a0, int a1,
    int a2, const char* what
)
{
    MString s;
    mstr_result_t res;

    if (MSTR_SUCC(mstr_create_empty(&s))) {
        res = mstr_format(&s, fmt, (usize_t)place, a0, a1, a2);
        ++g_checks;
        if (res != want) {
            ++g_failures;
            fprintf(
                stderr, "FAIL: %s: got %d, want %d\n", what, (int)res,
                (int)want
            );
        }
        mstr_clear(&s);
        mstr_free(&s);
    } else {
        ++g_checks;
        ++g_failures;
        fprintf(stderr, "FAIL: %s: mstr_create_empty failed\n", what);
    }
}

static void test_build_configure(void)
{
    uint32_t cfg_a = mstr_configure();
    uint32_t cfg_b = mstr_configure();

    // The configuration word must be stable and must self-report the
    // compiler family the recipe was built with.
    CHECK(cfg_a == cfg_b);
    CHECK(MSTR_CONFIGURE_CC_VAL(cfg_a) == MSTR_BUILD_CC);
}

static void test_integer_values(void)
{
    expect_format(
        "@{0:i32}@", 1, 0, "@123@", 123, 0, 0, "i32 decimal"
    );
    expect_format("@{0:i32}@", 1, 0, "@-1@", -1, 0, 0, "i32 negative");
    expect_format(
        "@{0:u32}@", 1, 0, "@4294967295@", (int)0xffffffff, 0, 0,
        "u32 max"
    );
    expect_format(
        "@{0:i8}#{1:i8}@", 2, 0, "@123#-1@", 123, -1, 0, "i8 pair"
    );
    expect_format(
        "@{0:i32}@", 1, 0, "@-2147483648@", (int)0x80000000, 0, 0,
        "i32 INT32_MIN"
    );
}

static void test_integer_styles(void)
{
    // 0xa5 = 165 dec / 245 oct / 101000101 bin / a5 hex
    expect_format(
        "@{0:i32:b}@", 1, 0, "@10100101@", 0xa5, 0, 0, "binary style"
    );
    expect_format("@{0:i32:o}@", 1, 0, "@245@", 0xa5, 0, 0, "octal style");
    expect_format(
        "@{0:i32:h}@{0:i32:H}@", 1, 0, "@a5@A5@", 0xa5, 0, 0,
        "hex style lower/upper"
    );
    expect_format(
        "@{0:i32:x}@{0:i32:X}@", 1, 0, "@0xa5@0XA5@", 0xa5, 0, 0,
        "hex style with prefix"
    );
    expect_format(
        "@{0:i32}@{0:i32:d}@", 1, 0, "@165@165@", 0xa5, 0, 0,
        "decimal style default/explicit"
    );
}

static void test_sign_and_align(void)
{
    expect_format(
        "@{0:i32:+}@{1:i32:+}@{2:i32:+}@", 3, 0, "@+123@-123@0@", 123, -123,
        0, "sign always"
    );
    expect_format(
        "@{0:i32:-}@{1:i32:-}@", 2, 0, "@123@-123@", 123, -123, 0,
        "sign never"
    );
    expect_format(
        "@{0:i32:<8}@", 1, 0, "@123     @", 123, 0, 0, "align left"
    );
    expect_format(
        "@{0:i32:#<8}@", 1, 0, "@123#####@", 123, 0, 0, "align left fill"
    );
    expect_format(
        "@{0:i32:>8}@", 1, 0, "@     123@", 123, 0, 0, "align right"
    );
    expect_format(
        "@{0:i32:#>8}@", 1, 0, "@#####123@", 123, 0, 0, "align right fill"
    );
    expect_format(
        "@{0:i32:=8}@", 1, 0, "@  123   @", 123, 0, 0, "align middle"
    );
    expect_format(
        "@{0:i32:#=8}@", 1, 0, "@##123###@", 123, 0, 0, "align middle fill"
    );
    expect_format(
        "@{0:i32:#>8}@", 1, 0, "@123456789@", 123456789, 0, 0,
        "align wider than width"
    );
}

static void test_argument_ids(void)
{
    expect_format(
        "@{0:i32}-{1:i32}-{0:i32}@", 2, 0, "@123-456-123@", 123, 456, 0,
        "repeated argument id"
    );
    expect_format(
        "@{{{0:i32}}}@", 1, 0, "@{1234}@", 1234, 0, 0, "escaped braces"
    );
    // Error paths: fewer placeholders than declared, out-of-order ids and a
    // repeated id with a different type must all be reported as such.
    expect_format_error(
        "@{0:i32}-{1:i32}@", 1, MStr_Err_InvaildArgumentID, 123, 0, 0,
        "too few declared arguments"
    );
    expect_format_error(
        "@{1:i32}-{0:i32}@", 2, MStr_Err_UnusedArgumentID, 123, 456, 0,
        "out-of-order argument id"
    );
    expect_format_error(
        "@{0:i32}-{0:u32}@", 1, MStr_Err_InvaildArgumentType, 123, 0, 0,
        "conflicting type for one id"
    );
    expect_format_error(
        "@{0:i32", 1, MStr_Err_MissingRightBrace, 1, 0, 0,
        "unterminated placeholder"
    );
    expect_format_error(
        "@{0:i32:v}@", 1, MStr_Err_UnsupportFormatType, 1, 0, 0,
        "unsupported format spec"
    );
}

static void test_string_api(void)
{
    MString a;
    MString b;

    if (MSTR_SUCC(mstr_create(&a, "MtFmT")) &&
        MSTR_SUCC(mstr_create_empty(&b))) {
        check_str(
            mstr_c_str(&a), "MtFmT", "mstr_create", __FILE__, __LINE__
        );
        CHECK(a.count == 5);
        CHECK(a.length == 5);

        CHECK(MSTR_SUCC(mstr_concat_cstr(&a, " on HarmonyOS")));
        check_str(
            mstr_c_str(&a), "MtFmT on HarmonyOS", "mstr_concat_cstr",
            __FILE__, __LINE__
        );
        CHECK(a.count == 18);

        CHECK(mstr_equal(&a, &a));
        CHECK(MSTR_SUCC(mstr_copy_from(&b, &a)));
        CHECK(mstr_equal(&a, &b));

        mstr_clear(&a);
        CHECK(a.count == 0);
        check_str(mstr_c_str(&a), "", "mstr_clear", __FILE__, __LINE__);

        mstr_free(&a);
        mstr_free(&b);
    } else {
        ++g_checks;
        ++g_failures;
        fprintf(stderr, "FAIL: mstr_create/mstr_create_empty failed\n");
    }
}

static void test_format_strings(void)
{
    // The `{...:s}` placeholder consumes a `const char *` from va_list — the
    // same path `mstr_ioformat` takes upstream.
    MString s;

    if (MSTR_SUCC(mstr_create_empty(&s))) {
        mstr_result_t res = mstr_format(
            &s, "@{0:s}|{1:s}@@", 2, "HarmonyOS", "PC"
        );
        ++g_checks;
        if (res != MStr_Ok) {
            ++g_failures;
            fprintf(
                stderr, "FAIL: string placeholders: mstr_format returned %d\n",
                (int)res
            );
        } else {
            check_str(
                mstr_c_str(&s), "@HarmonyOS|PC@@", "string placeholders",
                __FILE__, __LINE__
            );
        }
        mstr_free(&s);
    } else {
        ++g_checks;
        ++g_failures;
        fprintf(stderr, "FAIL: mstr_create_empty failed\n");
    }
}

static void test_heap_balance(void)
{
    usize_t alloc_cnt = 0;
    usize_t free_cnt = 0;
    MString s;

    // MString only keeps a 16-byte stack region, so reserving 512 bytes
    // forces the library's own heap manager (mstr_heap_init / *_sym
    // allocation) through a real allocate/free round trip.
    if (MSTR_SUCC(mstr_create_empty(&s))) {
        CHECK(MSTR_SUCC(mstr_reserve(&s, 512)));
        CHECK(MSTR_SUCC(mstr_concat_cstr(&s, "harmonyos-pc-adapter")));
        check_str(
            mstr_c_str(&s), "harmonyos-pc-adapter",
            "concat into reserved buffer", __FILE__, __LINE__
        );
        CHECK(s.count == 20);
        mstr_free(&s);
    } else {
        ++g_checks;
        ++g_failures;
        fprintf(stderr, "FAIL: mstr_create_empty failed\n");
    }

    mstr_heap_get_allocate_count(&alloc_cnt, &free_cnt);
    CHECK(alloc_cnt > 0);
    CHECK(alloc_cnt == free_cnt);
    CHECK(mstr_heap_get_free_size() > 0);
}

int main(void)
{
    mstr_heap_init(g_heap, HEAP_SIZE);

    test_build_configure();
    test_integer_values();
    test_integer_styles();
    test_sign_and_align();
    test_argument_ids();
    test_string_api();
    test_format_strings();
    test_heap_balance();

    printf(
        "mtfmt consumer: %u checks, %u failures\n", g_checks, g_failures
    );
    return g_failures == 0 ? 0 : 1;
}
