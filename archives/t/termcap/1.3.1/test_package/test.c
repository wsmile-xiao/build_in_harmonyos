/* Consumer test for GNU termcap 1.3.1 (R34): exercise the real database
 * API against an inline TERMCAP entry and assert the parsed capabilities.
 *
 * termcap.c tgetent() honours an inline $TERMCAP entry only when the
 * requested terminal name matches $TERM, so the test sets both.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termcap.h>

#define TERM_NAME "gtest"
#define TERM_ENTRY "gtest|GNU termcap consumer test:co#80:li#24:am:cl=\\E[2J:"

static int failures = 0;

static void check(int ok, const char *what) {
    printf("%s: %s\n", ok ? "PASS" : "FAIL", what);
    if (!ok)
        failures++;
}

int main(void) {
    char buf[2048];
    char area[256];
    char *area_ptr = area;
    int rc;

    if (setenv("TERM", TERM_NAME, 1) != 0 || setenv("TERMCAP", TERM_ENTRY, 1) != 0) {
        fprintf(stderr, "cannot set environment\n");
        return 2;
    }

    rc = tgetent(buf, TERM_NAME);
    check(rc == 1, "tgetent parses the inline TERMCAP entry");
    check(tgetnum("co") == 80, "tgetnum(co) == 80");
    check(tgetnum("li") == 24, "tgetnum(li) == 24");
    check(tgetnum("xy") == -1, "tgetnum(xy) reports missing capability as -1");
    check(tgetflag("am") == 1, "tgetflag(am) is set");
    check(tgetflag("xs") == 0, "tgetflag(xs) is unset");
    {
        const char *cl = tgetstr("cl", &area_ptr);
        check(cl != NULL && strcmp(cl, "\033[2J") == 0,
              "tgetstr(cl) expands \\E to ESC");
    }

    if (failures) {
        printf("%d check(s) FAILED\n", failures);
        return 1;
    }
    printf("termcap consumer test: all checks passed\n");
    return 0;
}
