#include <stdio.h>
#include <string.h>

#include <strcase.h>

static const char *dispatch(const char *cmd) {
    /* Runtime case-insensitive multiway branch on a string. */
    switch (strcase_tolower(cmd)) {
    case STRCASE(l, o, a, d):
        return "load";
    case STRCASE(d, u, m, p):
        return "dump";
    case STRCASE(s, t, a, t):
        return "stat";
    default:
        return "unknown";
    }
}

int main(void) {
    /* Real API assertions against the packaged strcase.h. */
    if (strcmp(dispatch("DUMP"), "dump") != 0) {
        fprintf(stderr, "dispatch(DUMP) mismatch\n");
        return 1;
    }
    if (strcmp(dispatch("Load"), "load") != 0) {
        fprintf(stderr, "dispatch(Load) mismatch\n");
        return 2;
    }
    if (strcmp(dispatch("bogus"), "unknown") != 0) {
        fprintf(stderr, "dispatch(bogus) should fall through\n");
        return 3;
    }
    /* Runtime strcase() matches the compile-time STRCASE constant. */
    if (strcase("abc") != STRCASE(a, b, c)) {
        fprintf(stderr, "strcase/STRCASE constant mismatch\n");
        return 4;
    }
    /* strcase_tolower folds case. */
    if (strcase_tolower("aBc") != strcase_tolower("abc")) {
        fprintf(stderr, "strcase_tolower case fold mismatch\n");
        return 5;
    }

    puts("strcase API assertions: 5 passed");
    return 0;
}
