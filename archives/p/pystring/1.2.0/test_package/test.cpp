#include <pystring/pystring.h>

#include <cstdio>
#include <string>
#include <vector>

int main() {
    const std::vector<std::string> parts = pystring::split("a,b,c", ",");
    if (parts.size() != 3) {
        std::printf("FAIL: split expected 3 parts, got %zu\n", parts.size());
        return 1;
    }

    const std::string joined = pystring::join("|", parts);
    if (joined != "a|b|c") {
        std::printf("FAIL: join expected 'a|b|c', got '%s'\n", joined.c_str());
        return 1;
    }

    const std::string stripped = pystring::strip("  hello  ");
    if (stripped != "hello") {
        std::printf("FAIL: strip expected 'hello', got '%s'\n", stripped.c_str());
        return 1;
    }

    const std::string upper = pystring::upper("hello");
    if (upper != "HELLO") {
        std::printf("FAIL: upper expected 'HELLO', got '%s'\n", upper.c_str());
        return 1;
    }

    std::puts("All pystring consumer checks passed");
    return 0;
}
