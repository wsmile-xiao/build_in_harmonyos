#include <pystring.h>
#include <stdio.h>

int main(void) {
    // Test pystring::split
    std::vector<std::string> parts = pystring::split("a,b,c", ",");
    if (parts.size() != 3) {
        printf("FAIL: split expected 3 parts, got %zu\n", parts.size());
        return 1;
    }

    // Test pystring::join
    std::string joined = pystring::join("|", parts);
    if (joined != "a|b|c") {
        printf("FAIL: join expected 'a|b|c', got '%s'\n", joined.c_str());
        return 1;
    }

    // Test pystring::strip
    std::string stripped = pystring::strip("  hello  ");
    if (stripped != "hello") {
        printf("FAIL: strip expected 'hello', got '%s'\n", stripped.c_str());
        return 1;
    }

    // Test pystring::upper
    std::string upper = pystring::upper("hello");
    if (upper != "HELLO") {
        printf("FAIL: upper expected 'HELLO', got '%s'\n", upper.c_str());
        return 1;
    }

    printf("All pystring tests PASSED\n");
    return 0;
}
