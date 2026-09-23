#include <stdio.h>
#include <string.h>

#include <pcre2posix.h>

#define CHECK(condition, message)                                              \
    do {                                                                       \
        if (!(condition)) {                                                    \
            fprintf(stderr, "check failed: %s\n", (message));               \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main(void)
{
    regex_t expression;
    regmatch_t matches[2];

    CHECK(regcomp(&expression, "^hello-([0-9]+)$", REG_EXTENDED) == 0,
          "compile POSIX expression");
    CHECK(regexec(&expression, "hello-2047", 2, matches, 0) == 0,
          "execute POSIX expression");
    CHECK(matches[0].rm_so == 0 && matches[0].rm_eo == 10,
          "validate full POSIX match");
    CHECK(matches[1].rm_so == 6 && matches[1].rm_eo == 10,
          "validate POSIX capture");
    CHECK(regexec(&expression, "goodbye", 2, matches, 0) == REG_NOMATCH,
          "reject a non-matching subject");
    regfree(&expression);

    int invalid = regcomp(&expression, "(", REG_EXTENDED);
    CHECK(invalid != 0, "reject an invalid POSIX expression");
    char error_text[128];
    CHECK(regerror(invalid, &expression, error_text, sizeof(error_text)) > 0 &&
              strlen(error_text) > 0,
          "format the POSIX compile error");
    regfree(&expression);
    return 0;
}
