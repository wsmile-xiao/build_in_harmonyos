#include <cstdio>
#include <string>
#include <vector>

#include "zpp_bits.h"

// Consumer test: serialize + deserialize a struct with zpp::bits
// (R34: must actually exercise the tested package's API).
int main() {
    struct data {
        std::vector<int> v;
        std::string s;
        int x;
    };
    data in{{1, 2, 3, 42}, "hello-ohos", 2026};
    auto [bytes, in_a, out_a] = zpp::bits::data_in_out();
    if (zpp::bits::failure(out_a(in))) {
        std::puts("FAIL: serialize");
        return 1;
    }
    data out_d;
    if (zpp::bits::failure(in_a(out_d))) {
        std::puts("FAIL: deserialize");
        return 1;
    }
    if (out_d.v != in.v || out_d.s != in.s || out_d.x != in.x) {
        std::puts("FAIL: round-trip mismatch");
        return 1;
    }
    std::printf("PASS: zpp_bits round-trip ok (%zu bytes)\n", bytes.size());
    return 0;
}
