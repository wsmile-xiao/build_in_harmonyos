// OHOS 专项测试：crc_cpp 1.2.0 — 在 OHOS aarch64 上验证公开 API
// 覆盖：多算法已知向量、constexpr 编译期计算、tiny/small/large 表实现一致性
#include "crc_cpp.h"
#include <cstdint>
#include <cstdio>
#include <cstring>

// 已知标准向量 "123456789" 的 CRC 校验和（与上游 test.cpp 同源向量）
struct Vector { const char* name; crc_cpp::crc32::accumulator_type crc32_value; };

static bool test_crc32_known_vector()
{
    const char msg[] = "123456789";
    crc_cpp::crc32 crc;
    for (size_t i = 0; i < strlen(msg); i++) crc.update((uint8_t)msg[i]);
    uint32_t r = crc.final();
    bool ok = (r == 0xCBF43926u);
    std::printf("  crc32 known vector: got 0x%08X expected 0xCBF43926 -> %s\n", (unsigned)r, ok ? "PASS" : "FAIL");
    return ok;
}

static bool test_crc16_ccit_known_vector()
{
    const char msg[] = "123456789";
    crc_cpp::crc16_ccit crc;
    for (size_t i = 0; i < strlen(msg); i++) crc.update((uint8_t)msg[i]);
    uint16_t r = crc.final();
    bool ok = (r == 0x29B1u);
    std::printf("  crc16_ccit known vector: got 0x%04X expected 0x29B1 -> %s\n", (unsigned)r, ok ? "PASS" : "FAIL");
    return ok;
}

// 编译期 constexpr 计算验证（上游 README 承诺的特性）
constexpr bool constexpr_crc()
{
    constexpr char msg[] = "123456789";
    crc_cpp::crc8 crc;
    for (size_t i = 0; i < 9; i++) crc.update((uint8_t)msg[i]);
    return crc.final() == 0xF4u;
}
static_assert(constexpr_crc(), "constexpr CRC8 computation failed");

// tiny/small/large 三种表实现必须给出相同结果
template<template<const crc_cpp::table_size> class TCrc>
static bool check_table_consistency()
{
    const char msg[] = "123456789";
    uint32_t expected = 0;
    bool first = true, ok = true;
    for (auto ts : { crc_cpp::table_size::tiny, crc_cpp::table_size::small, crc_cpp::table_size::large }) {
        typename TCrc<crc_cpp::table_size::small>::accumulator_type v = 0;
        if (ts == crc_cpp::table_size::tiny) {
            TCrc<crc_cpp::table_size::tiny> c;
            for (size_t i = 0; i < 9; i++) c.update((uint8_t)msg[i]);
            v = c.final();
        } else if (ts == crc_cpp::table_size::small) {
            TCrc<crc_cpp::table_size::small> c;
            for (size_t i = 0; i < 9; i++) c.update((uint8_t)msg[i]);
            v = c.final();
        } else {
            TCrc<crc_cpp::table_size::large> c;
            for (size_t i = 0; i < 9; i++) c.update((uint8_t)msg[i]);
            v = c.final();
        }
        if (first) { expected = (uint32_t)v; first = false; }
        else if ((uint32_t)v != expected) ok = false;
    }
    std::printf("  crc32 table-size consistency (tiny/small/large): %s\n", ok ? "PASS" : "FAIL");
    return ok;
}

int main()
{
    std::printf("OHOS-specific test: crc_cpp 1.2.0 on aarch64-linux-ohos (clang %d)\n", __clang_major__);
    bool all = true;
    all &= test_crc32_known_vector();
    all &= test_crc16_ccit_known_vector();
    all &= check_table_consistency<crc_cpp::family::crc32>();
    std::printf("RESULT: %s\n", all ? "ALL PASS" : "FAILURE");
    return all ? 0 : 1;
}
