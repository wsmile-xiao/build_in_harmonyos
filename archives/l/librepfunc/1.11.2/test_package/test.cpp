#include <cassert>
#include <cstdio>
#include <string>
#include <repfunc.h>

int main() {
    // UpperCase / LowerCase round-trip
    std::string up = UpperCase("librepfunc");
    assert(up == "LIBREFUNC");
    // IntToStr
    assert(IntToStr(12345) == "12345");
    // IntToHex
    assert(IntToHex(255, 2) == "0xff");
    // Trim
    assert(Trim("  padded  ") == "padded");
    std::printf("librepfunc consumer test: OK\n");
    return 0;
}