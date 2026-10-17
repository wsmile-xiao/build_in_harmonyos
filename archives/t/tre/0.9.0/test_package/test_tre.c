#include <stdio.h>
#include <tre/tre.h>

static int test_basic_match(void) {
    regex_t preg;
    const char *pattern = "hello";
    const char *text = "hello world";
    int err = regcomp(&preg, pattern, REG_EXTENDED);
    if (err != 0) { fprintf(stderr, "regcomp failed\n"); return 0; }
    regmatch_t match;
    err = regexec(&preg, text, 1, &match, 0);
    regfree(&preg);
    if (err != 0) { fprintf(stderr, "FAIL: basic match\n"); return 0; }
    printf("PASS: basic match: '%s' in '%s'\n", pattern, text);
    return 1;
}

static int test_no_match(void) {
    regex_t preg;
    int err = regcomp(&preg, "^[0-9]+$", REG_EXTENDED);
    if (err != 0) { fprintf(stderr, "regcomp failed\n"); return 0; }
    err = regexec(&preg, "abc", 0, NULL, 0);
    regfree(&preg);
    if (err != REG_NOMATCH) { fprintf(stderr, "FAIL: no match\n"); return 0; }
    printf("PASS: no match\n");
    return 1;
}

int main(void) {
    int passed = 0, total = 2;
    passed += test_basic_match();
    passed += test_no_match();
    printf("=== %d/%d tests passed ===\n", passed, total);
    return (passed == total) ? 0 : 1;
}
