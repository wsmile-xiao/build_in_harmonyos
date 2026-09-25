// test_package 消费者测试 — crc_cpp 1.2.0
// 真实调用 crc_cpp 公开 API：对 "123456789" 计算 crc32/crc16_ccit/crc8 并
// 校验已知标准向量（R34 非空壳；仅使用安装后的公开头文件 crc_cpp.h）。
#include <cstdio>
#include <cstdint>
#include <cstring>
#include "crc_cpp.h"

int main() {
    const char msg[] = "123456789";
    int fails = 0;

    crc_cpp::crc32 c32;
    for (size_t i = 0; i < strlen(msg); i++) c32.update((uint8_t)msg[i]);
    uint32_t r32 = c32.final();
    bool ok32 = (r32 == 0xCBF43926u);
    std::printf("crc32(\"123456789\") = 0x%08X expected 0xCBF43926 -> %s\n",
                (unsigned)r32, ok32 ? "PASS" : "FAIL");
    if (!ok32) fails++;

    crc_cpp::crc16_ccit c16;
    for (size_t i = 0; i < strlen(msg); i++) c16.update((uint8_t)msg[i]);
    uint16_t r16 = c16.final();
    bool ok16 = (r16 == 0x29B1u);
    std::printf("crc16_ccit(\"123456789\") = 0x%04X expected 0x29B1 -> %s\n",
                (unsigned)r16, ok16 ? "PASS" : "FAIL");
    if (!ok16) fails++;

    crc_cpp::crc8 c8;
    for (size_t i = 0; i < strlen(msg); i++) c8.update((uint8_t)msg[i]);
    uint8_t r8 = c8.final();
    bool ok8 = (r8 == 0xF4u);
    std::printf("crc8(\"123456789\") = 0x%02X expected 0xF4 -> %s\n",
                (unsigned)r8, ok8 ? "PASS" : "FAIL");
    if (!ok8) fails++;

    std::printf("test_crc_cpp: %s (%d fails)\n", fails == 0 ? "ALL PASS" : "FAILURE", fails);
    return fails == 0 ? 0 : 1;
}
