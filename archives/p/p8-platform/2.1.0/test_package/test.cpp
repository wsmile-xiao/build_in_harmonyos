#include <stdio.h>
#include <string>
#include "p8-platform/util/StringUtils.h"

int main(void) {
    // Test StringUtils::ToUpper
    std::string s = "hello";
    StringUtils::ToUpper(s);
    if (s != "HELLO") {
        printf("FAIL: ToUpper expected 'HELLO', got '%s'\n", s.c_str());
        return 1;
    }

    // Test StringUtils::Trim
    std::string t = "  spaced  ";
    StringUtils::Trim(t);
    if (t != "spaced") {
        printf("FAIL: Trim expected 'spaced', got '%s'\n", t.c_str());
        return 1;
    }

    // Test StringUtils::EqualsNoCase
    if (!StringUtils::EqualsNoCase("Hello", "hello")) {
        printf("FAIL: EqualsNoCase('Hello','hello') should be true\n");
        return 1;
    }

    printf("test p8-platform 2.1.0: OK\n");
    return 0;
}
