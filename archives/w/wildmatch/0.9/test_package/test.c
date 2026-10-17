#include <stdio.h>
#include <wildmatch/wildmatch.h>

int main(void) {
    // Test basic pattern matching
    if (wildmatch("foo", "foo", 0) == WM_MATCH) {
        printf("Test 1 passed: 'foo' matches 'foo'\n");
    } else {
        fprintf(stderr, "Test 1 failed\n");
        return 1;
    }

    // Test wildcard matching
    if (wildmatch("foo*", "foobar", 0) == WM_MATCH) {
        printf("Test 2 passed: 'foo*' matches 'foobar'\n");
    } else {
        fprintf(stderr, "Test 2 failed\n");
        return 1;
    }

    // Test no match case
    if (wildmatch("foo", "bar", 0) == WM_NOMATCH) {
        printf("Test 3 passed: 'foo' does not match 'bar'\n");
    } else {
        fprintf(stderr, "Test 3 failed\n");
        return 1;
    }

    printf("All wildmatch tests passed!\n");
    return 0;
}
