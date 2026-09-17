// test_package/test.cpp — dbg-macro 0.5.1.1 consumer test
#include <dbg.h>
#include <cstdint>
#include <cstdio>
#include <sstream>
#include <string>
#include <vector>

int main() {
    int x = 42;
    int y = dbg(x);

    if (y != 42) {
        fprintf(stderr, "FAIL: dbg() did not return the value (got %d)\n", y);
        return 1;
    }

    int multiple = dbg(1, 2, 1 + 2);
    if (multiple != 3) {
        fprintf(stderr, "FAIL: multiple-argument dbg() returned %d\n", multiple);
        return 1;
    }

    std::stringstream container;
    dbg::pretty_print(container, std::vector<int>{1, 2, 3});
    if (container.str() != "{1, 2, 3}") {
        fprintf(stderr, "FAIL: pretty_print(vector) produced '%s'\n",
                container.str().c_str());
        return 1;
    }

    std::stringstream hex;
    dbg::pretty_print(hex, dbg::hex(static_cast<std::uint16_t>(0xAB12)));
    if (hex.str() != "0xAB12") {
        fprintf(stderr, "FAIL: dbg::hex output produced '%s'\n",
                hex.str().c_str());
        return 1;
    }

    std::stringstream bin;
    dbg::pretty_print(bin, dbg::bin(static_cast<std::uint8_t>(11)));
    if (bin.str() != "0b00001011") {
        fprintf(stderr, "FAIL: dbg::bin output produced '%s'\n",
                bin.str().c_str());
        return 1;
    }

    printf("dbg-macro consumer test: PASS (5 assertions)\n");
    return 0;
}
