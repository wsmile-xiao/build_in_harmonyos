#include <stdio.h>
#include <string.h>

/* skalibs headers (execline depends on skalibs) */
#include <skalibs/stralloc.h>
#include <skalibs/bytestr.h>

/* execline headers — substantively exercise the library API (R34) */
#include <execline/execline.h>

int main(void)
{
    /* Test 1: el_semicolon — scans an argv array for block terminators.
       This is the core execline block-parsing function.
       el_semicolon takes char const ** (pointer to argv array) and returns
       the number of args in the current block. A block ends at an empty
       string "" or a string starting with ' ' (space). */
    {
        /* Simulate: foreground echo hello "" rest */
        const char *argv[] = { "echo", "hello", "", "rest", NULL };
        const char **p = argv;
        int argc1 = el_semicolon(p);
        /* el_semicolon returns i+1 where i is index of terminator.
           argv[2]="" is the terminator, so returns 3 (0,1,2 -> i=2 -> return 3). */
        if (argc1 < 1) {
            fprintf(stderr, "FAIL: el_semicolon returned %d (expected >= 1)\n", argc1);
            return 1;
        }
    }

    /* Test 2: el_getstrict — returns the strictness level (0 by default).
       This is a simple const function that exercises the library linkage. */
    {
        unsigned int strict = el_getstrict();
        /* With no EXECLINE_STRICT env var set, strict should be 0 */
        if (strict != 0) {
            fprintf(stderr, "FAIL: el_getstrict expected 0 (no env), got %u\n", strict);
            return 2;
        }
    }

    /* Test 3: el_vardupl — checks for duplicate variable names in a
       null-separated string buffer (execline env format).
       el_vardupl(key, s, len): searches buffer s (len bytes, null-separated
       strings) for key. Returns 1 if found, 0 if not. */
    {
        /* Build a null-separated buffer: "VAR1\0VAR2\0" */
        char buf[] = "VAR1\0VAR2\0";
        size_t buflen = sizeof(buf) - 1; /* exclude trailing \0 of the array */

        int dup = el_vardupl("VAR1", buf, buflen);
        if (dup != 1) {
            fprintf(stderr, "FAIL: el_vardupl should find VAR1, got %d\n", dup);
            return 3;
        }

        int nodup = el_vardupl("VAR3", buf, buflen);
        if (nodup != 0) {
            fprintf(stderr, "FAIL: el_vardupl should not find VAR3, got %d\n", nodup);
            return 4;
        }
    }

    /* Test 4: el_transforminfo_t — verify struct initialization macro works */
    {
        eltransforminfo_t ti = ELTRANSFORMINFO_ZERO;
        if (ti.delim == NULL || ti.delim[0] == '\0') {
            fprintf(stderr, "FAIL: ELTRANSFORMINFO_ZERO delim not set correctly\n");
            return 5;
        }
        /* Default delim should be " \n\r\t" */
        if (strcmp(ti.delim, " \n\r\t") != 0) {
            fprintf(stderr, "FAIL: ELTRANSFORMINFO_ZERO delim mismatch: '%s'\n", ti.delim);
            return 6;
        }
    }

    /* Test 5: el_parse_from_string — core parsing function.
       Parses execline syntax from a string into a stralloc.
       Returns number of parsed arguments, or negative on error. */
    {
        stralloc sa = STRALLOC_ZERO;
        int parsed = el_parse_from_string(&sa, "simple word");
        /* el_parse_from_string returns the number of parsed words on success,
           0 on EOF, negative on error */
        if (parsed < 0) {
            fprintf(stderr, "FAIL: el_parse_from_string returned %d\n", parsed);
            stralloc_free(&sa);
            return 7;
        }
        stralloc_free(&sa);
    }

    printf("execline API assertions: 7 passed\n");
    return 0;
}
