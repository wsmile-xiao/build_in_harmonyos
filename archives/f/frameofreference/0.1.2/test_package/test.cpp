// test.cpp — consumer test for frameofreference 0.1.2
// 实质调用被测包 API：pack4_8 / unpack4_8 往返一致性验证（R34）
#include <cstdint>
#include <cstdio>
#include <vector>
#include "bpacking.h"
#include "compression.h"

int main() {
    // 8 个 4-bit 值（0..15），使用 pack4_8 / unpack4_8 往返
    const uint32_t base = 100;
    uint32_t in[8] = {100, 101, 102, 103, 104, 105, 106, 107};
    uint32_t packed[8] = {0};
    uint32_t out[8] = {0};

    uint32_t *pend = pack4_8(base, in, packed);
    uint32_t *oend = unpack4_8(base, packed, out);
    if (pend == nullptr || oend == nullptr) {
        printf("FAIL: pack/unpack returned null\n");
        return 1;
    }
    for (int i = 0; i < 8; ++i) {
        if (out[i] != in[i]) {
            printf("FAIL: roundtrip mismatch at %d: got %u want %u\n", i, out[i], in[i]);
            return 1;
        }
    }

    // compress/uncompress 往返（上游 unit() 同款路径）
    std::vector<uint32_t> test;
    for (uint32_t i = 0; i < 100; ++i) test.push_back(i);
    std::vector<uint32_t> comp(test.size() + 1024);
    std::vector<uint32_t> recover(test.size() + 1024);
    compress(test.data(), test.size(), comp.data());
    uint32_t nvalue = 0;
    uncompress(comp.data(), recover.data(), nvalue);
    recover.resize(nvalue);
    if (recover != test) {
        printf("FAIL: compress/uncompress roundtrip mismatch\n");
        return 1;
    }

    printf("test frameofreference 0.1.2: OK (pack4_8/unpack4_8 + compress/uncompress roundtrip)\n");
    return 0;
}
