/* Consumer test for slre 1.3 — validates slre_match() against basic patterns. */
#include "slre.h"
#include <stdio.h>
#include <string.h>

static int g_checks = 0;
static int g_failed = 0;
#define CHECK(cond) do { ++g_checks; if (!(cond)) { ++g_failed; printf("FAIL: %s\n", #cond); } } while(0)

int main(void) {
    struct slre_cap caps[4];

    CHECK(slre_match(".", "abcd", 4, NULL, 0) == 1);
    CHECK(slre_match("x", "abcd", 4, NULL, 0) == SLRE_NO_MATCH);
    CHECK(slre_match("[0-9]+", "abc12345", 8, NULL, 0) == 8);
    CHECK(slre_match("(?i)HELLO", "hello world", 11, NULL, 0) == 5);

    memset(caps, 0, sizeof(caps));
    int n = slre_match("(\\d+)-(\\d+)", "42-7 ok", 7, caps, 2);
    CHECK(n == 4);
    CHECK(caps[0].len == 2 && strncmp(caps[0].ptr, "42", 2) == 0);
    CHECK(caps[1].len == 1 && strncmp(caps[1].ptr, "7", 1) == 0);

    CHECK(slre_match("(", "abc", 3, NULL, 0) == SLRE_UNBALANCED_BRACKETS);
    CHECK(slre_match("^a.c$", "abc", 3, NULL, 0) == 3);
    CHECK(slre_match("\\x41", "A", 1, NULL, 0) == 1);

    printf("slre test_package: %d checks, %d failed\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
