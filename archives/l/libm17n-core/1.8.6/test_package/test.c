/* test.c — consumer-side verification of libm17n-core (m17n-lib 1.8.6).
 *
 * The adapted library is exercised through its public CORE API only, so the
 * test needs no m17n-db data package and proves that the shared library built
 * for the target platform is both loadable and functional:
 *
 *   [1] version macros from the public header
 *   [2] MSymbol   — interning, lookup, symbol properties
 *   [3] MPlist    — property list creation, append, prepend, pop, length
 *   [4] MCharTable— character table set/lookup/default/range
 *   [5] MText     — M-text creation, append, insert, delete, compare,
 *                   search, duplicate and text properties
 *
 * Exit code 0 means every assertion passed.
 */
#include <m17n-core.h>
#include <m17n-misc.h>

#include <stdio.h>
#include <string.h>

static int checks;
static int failures;

/* "XHi" followed by U+4E2D (CJK ideograph) as UTF-8 bytes. */
static const char utf8_text[] = "XHi\xe4\xb8\xad";
static const char utf8_cjk[] = "\xe4\xb8\xad";

#define CHECK(cond, what)                                             \
    do {                                                              \
        checks++;                                                     \
        if (cond) {                                                   \
            printf("  ok   %s\n", what);                              \
        } else {                                                      \
            printf("  FAIL %s (test.c:%d)\n", what, __LINE__);        \
            failures++;                                               \
        }                                                             \
    } while (0)

int main(void)
{
    M17N_INIT();

    printf("[1] version\n");
    CHECK(strcmp(M17NLIB_VERSION_NAME, "1.8.6") == 0,
          "public header reports version 1.8.6");
    CHECK(M17NLIB_MAJOR_VERSION == 1 && M17NLIB_MINOR_VERSION == 8
              && M17NLIB_PATCH_LEVEL == 6,
          "version macros agree with the release");

    printf("[2] symbol table (MSymbol)\n");
    MSymbol sym = msymbol("libm17n-core-probe");
    CHECK(sym != Mnil, "msymbol() interns a new symbol");
    if (sym != Mnil) {
        CHECK(strcmp(msymbol_name(sym), "libm17n-core-probe") == 0,
              "msymbol_name() round-trips the name");
        CHECK(msymbol_exist("libm17n-core-probe") == sym,
              "msymbol_exist() finds the interned symbol");
        CHECK(msymbol_exist("libm17n-core-absent") == Mnil,
              "msymbol_exist() reports Mnil for an unknown name");
        CHECK(msymbol_exist(msymbol_name(Mt)) == Mt,
              "the built-in managing key Mt is interned in the symbol table");

        MSymbol key = msymbol("probe-key");
        CHECK(msymbol_put(sym, key, (void *) 0x42) == 0,
              "msymbol_put() succeeds");
        CHECK(msymbol_get(sym, key) == (void *) 0x42,
              "msymbol_get() returns the stored value");
        CHECK(msymbol_get(sym, msymbol("probe-key-absent")) == NULL,
              "msymbol_get() returns NULL for a missing key");
        CHECK(merror_code == MERROR_NONE,
              "no error is pending after the symbol calls");
    }

    printf("[3] property list (MPlist)\n");
    {
        MPlist *pl = mplist();
        CHECK(pl != NULL, "mplist() creates a property list");
        CHECK(mplist_length(pl) == 0, "a fresh property list is empty");

        pl = mplist_add(pl, Minteger, (void *) 7);
        CHECK(pl != NULL && mplist_length(pl) == 1,
              "mplist_add() appends one element");
        CHECK(mplist_key(pl) == Minteger, "element key is Minteger");
        CHECK((int) (long) mplist_value(pl) == 7, "element value round-trips");
        CHECK(mplist_length(mplist_next(pl)) == 0,
              "the appended element is followed by the tail");

        pl = mplist_push(pl, Msymbol, (void *) sym);
        CHECK(mplist_length(pl) == 2, "mplist_push() prepends an element");
        CHECK(mplist_key(pl) == Msymbol && mplist_value(pl) == (void *) sym,
              "the prepended element holds the symbol");
        CHECK(mplist_pop(pl) == (void *) sym,
              "mplist_pop() returns the first value");
        CHECK(mplist_length(pl) == 1, "mplist_pop() shrinks the list");
        CHECK(mplist_find_by_key(pl, Minteger) != NULL,
              "mplist_find_by_key() locates the remaining element");
        CHECK(mplist_find_by_key(pl, msymbol("probe-key-absent")) == NULL,
              "mplist_find_by_key() returns NULL for a missing key");
    }

    printf("[4] character table (MCharTable)\n");
    {
        MCharTable *ct = mchartable(msymbol("probe-chartable"),
                                    (void *) 0xabc);
        CHECK(ct != NULL, "mchartable() creates a character table");
        CHECK(mchartable_lookup(ct, 'A') == (void *) 0xabc,
              "unset characters return the default value");
        CHECK(mchartable_set(ct, 'A', (void *) 65) == 0,
              "mchartable_set() succeeds");
        CHECK(mchartable_lookup(ct, 'A') == (void *) 65,
              "mchartable_lookup() returns the stored value");
        CHECK(mchartable_lookup(ct, 'B') == (void *) 0xabc,
              "neighbouring characters keep the default value");
        CHECK(mchartable_min_char(ct) <= 'A' && mchartable_max_char(ct) >= 'A',
              "min/max character bound the assigned range");

        int from = -1;
        int to = -1;
        mchartable_range(ct, &from, &to);
        CHECK(from <= 'A' && 'A' <= to,
              "mchartable_range() covers the assigned character");
    }

    printf("[5] M-text (MText)\n");
    {
        MText *mt = mtext();
        CHECK(mt != NULL, "mtext() creates an M-text");
        CHECK(mtext_len(mt) == 0, "a fresh M-text is empty");

        CHECK(mtext_cat_char(mt, 'H') == mt, "mtext_cat_char() appends");
        mtext_cat_char(mt, 'i');
        mtext_cat_char(mt, 0x4e2d);   /* U+4E2D CJK ideograph */
        CHECK(mtext_len(mt) == 3, "three characters were appended");
        CHECK(mtext_ref_char(mt, 0) == 'H', "first character is 'H'");
        CHECK(mtext_ref_char(mt, 1) == 'i', "second character is 'i'");
        CHECK(mtext_ref_char(mt, 2) == 0x4e2d,
              "non-ASCII character survives round-trip");

        CHECK(mtext_ins_char(mt, 0, 'X', 1) == 0,
              "mtext_ins_char() succeeds");
        CHECK(mtext_len(mt) == 4 && mtext_ref_char(mt, 0) == 'X',
              "inserted character is at the head");

        MText *copy = mtext_dup(mt);
        CHECK(copy != NULL && mtext_cmp(copy, mt) == 0,
              "mtext_dup() copies and mtext_cmp() compares equal");

        /* mtext_search()/mtext_text() only work on a UTF-8/ASCII internal
           format (mtext.c: mt1->format > MTEXT_FORMAT_UTF_8 -> MERROR), so the
           search haystack is built with the raw-data constructor. */
        MText *utf8 = mtext_from_data(utf8_text, (int) sizeof(utf8_text) - 1,
                                      MTEXT_FORMAT_UTF_8);
        CHECK(utf8 != NULL, "mtext_from_data() builds a UTF-8 M-text");
        CHECK(mtext_len(utf8) == 4, "the UTF-8 M-text holds 4 characters");
        CHECK(mtext_ref_char(utf8, 3) == 0x4e2d,
              "U+4E2D is decoded from its UTF-8 bytes");
        CHECK(mtext_cmp(utf8, mt) == 0,
              "cross-format mtext_cmp() sees identical text");

        MText *needle = mtext_from_data(utf8_cjk, (int) sizeof(utf8_cjk) - 1,
                                        MTEXT_FORMAT_UTF_8);
        CHECK(needle != NULL && mtext_len(needle) == 1,
              "the search needle is one UTF-8 character");
        MText *absent = mtext_from_data("zzz", 3, MTEXT_FORMAT_UTF_8);

        /* mtext_search(mt1, from, to, mt2): TO is the end of the match region
           and mtext.c subtracts the needle length before scanning, so the
           region must reach one position past the match. */
        CHECK(mtext_search(utf8, 0, mtext_len(utf8) + 1, needle) == 3,
              "mtext_search() finds U+4E2D at position 3");
        CHECK(mtext_search(utf8, 0, mtext_len(utf8) + 1, absent) == -1,
              "mtext_search() reports -1 for an absent pattern");
        CHECK(mtext_text(utf8, 0, needle) == 3,
              "mtext_text() locates U+4E2D as well");
        CHECK(mtext_chr(utf8, 0x4e2d) == 3,
              "mtext_chr() returns the index of U+4E2D");

        MText *part = mtext_duplicate(mt, 1, 3);
        CHECK(part != NULL && mtext_len(part) == 2,
              "mtext_duplicate() extracts a sub-range");

        CHECK(mtext_del(mt, 0, 1) == 0 && mtext_len(mt) == 3,
              "mtext_del() removes the head character");
        CHECK(mtext_cmp(mt, copy) != 0,
              "the modified M-text differs from its copy");

        MSymbol prop = msymbol("probe-text-property");
        CHECK(mtext_put_prop(mt, 1, 3, prop, (void *) 0x99) == 0,
              "mtext_put_prop() attaches a text property");
        CHECK(mtext_get_prop(mt, 1, prop) == (void *) 0x99,
              "mtext_get_prop() reads the value inside the range");
        CHECK(mtext_get_prop(mt, 0, prop) == NULL,
              "the property does not leak outside the range");
        int pfrom = -1;
        int pto = -1;
        CHECK(mtext_prop_range(mt, prop, 1, &pfrom, &pto, 0) > 0
                  && pfrom == 1 && pto == 3,
              "mtext_prop_range() reports the attached range");
    }

    M17N_FINI();

    printf("\n%d checks, %d failure(s)\n", checks, failures);
    if (failures) {
        printf("RESULT: FAILED\n");
        return 1;
    }
    printf("RESULT: PASSED\n");
    return 0;
}
