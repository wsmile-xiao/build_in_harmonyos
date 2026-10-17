#include <sds.h>

#include <stdio.h>
#include <string.h>

#define CHECK(condition, message) do { \
    if (!(condition)) { \
        fprintf(stderr, "FAIL: %s\n", message); \
        failures++; \
    } \
} while (0)

int main(void) {
    const char binary[] = {'A', '\0', 'B'};
    sds value = sdsnew("hello");
    sds joined;
    sds *parts;
    int count = 0;
    int failures = 0;

    CHECK(value != NULL && sdslen(value) == 5 && strcmp(value, "hello") == 0,
          "create an SDS string");

    value = sdscatlen(value, binary, sizeof(binary));
    CHECK(sdslen(value) == 8 && memcmp(value + 5, binary, sizeof(binary)) == 0,
          "append binary-safe content");

    sdsclear(value);
    value = sdscatfmt(value, "%s:%i", "item", 42);
    CHECK(strcmp(value, "item:42") == 0,
          "append formatted text");

    value = sdscat(value, "  ");
    sdstrim(value, " ");
    CHECK(strcmp(value, "item:42") == 0,
          "trim matching characters");

    sdsrange(value, 5, -1);
    CHECK(strcmp(value, "42") == 0,
          "select a string range");

    parts = sdssplitlen("alpha,beta,gamma", 16, ",", 1, &count);
    CHECK(parts != NULL && count == 3 && strcmp(parts[1], "beta") == 0,
          "split a string into tokens");

    joined = sdsjoinsds(parts, count, "|", 1);
    CHECK(joined != NULL && strcmp(joined, "alpha|beta|gamma") == 0,
          "join SDS tokens");
    CHECK(sdslen(joined) == strlen("alpha|beta|gamma"),
          "preserve joined-string length metadata");

    sdsfree(joined);
    sdsfreesplitres(parts, count);
    sdsfree(value);

    if (failures != 0) {
        fprintf(stderr, "SDS consumer test failed: %d assertion(s)\n", failures);
        return 1;
    }
    puts("SDS consumer test passed: 8 assertions");
    return 0;
}
