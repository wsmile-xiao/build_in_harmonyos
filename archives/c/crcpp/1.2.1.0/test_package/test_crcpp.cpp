/**
 * 消费者测试 — crcpp 1.2.1.0（header-only 交付形态）
 *
 * 以消费者视角 include <CRC.h>（来自 conan 包的 include/ 交付件），真实调用
 * CRC::Calculate / CRC::CalculateBits / CRC::Table 接口并断言计算结果，
 * 覆盖：自报版本、逐位与查表两条计算路径、multipart 续算、非 8 位整倍数
 * 输入、参数结构体字段。逐条打印读数（PASS/FAIL + got/want），
 * 任何一条失败即退出码非 0。
 *
 * 断言口径：13 条运行期断言（check 计数）+ 1 条编译期 static_assert（版本宏）。
 * 期望值与上游 test/src/main.cpp 的 CHECK("123456789") 期望值一致。
 */
#include <CRC.h>

#include <cstdint>
#include <cstdio>

// ── 编译期断言：交付头自报版本必须与包版本一致 ────────────────────────────
static_assert(CRCPP_MAJOR_VERSION == 1 && CRCPP_MINOR_VERSION == 2 &&
                  CRCPP_PATCH_VERSION == 1 && CRCPP_REVISION_VERSION == 0,
              "CRC.h must self-report version 1.2.1.0");

static int g_total = 0;
static int g_failed = 0;

static void Check(const char * name, std::uint64_t got, std::uint64_t want)
{
    ++g_total;
    if (got == want)
    {
        std::printf("[consumer] PASS %-44s got=0x%llX\n",
                    name, static_cast<unsigned long long>(got));
    }
    else
    {
        ++g_failed;
        std::printf("[consumer] FAIL %-44s got=0x%llX want=0x%llX\n",
                    name, static_cast<unsigned long long>(got),
                    static_cast<unsigned long long>(want));
    }
}

int main()
{
    static const char CHECK_DATA[] = "123456789";
    const std::size_t CHECK_SIZE = sizeof(CHECK_DATA) - 1;

    // 1. 交付头自报版本 == 1.2.1.0（打包的就是这一份）
    const std::uint64_t packed =
        (static_cast<std::uint64_t>(CRCPP_MAJOR_VERSION) << 24) |
        (static_cast<std::uint64_t>(CRCPP_MINOR_VERSION) << 16) |
        (static_cast<std::uint64_t>(CRCPP_PATCH_VERSION) << 8) |
        static_cast<std::uint64_t>(CRCPP_REVISION_VERSION);
    Check("CRC.h self-reported version == 1.2.1.0", packed, 0x01020100ull);

    // 2/3. CRC-32/ISO-HDLC：逐位与查表两条路径
    Check("CRC-32/ISO-HDLC bitwise",
          CRC::Calculate(CHECK_DATA, CHECK_SIZE, CRC::CRC_32()), 0xCBF43926ull);
    {
        CRC::Table<std::uint32_t, 32> table(CRC::CRC_32());
        Check("CRC-32/ISO-HDLC table",
              CRC::Calculate(CHECK_DATA, CHECK_SIZE, table), 0xCBF43926ull);
    }

    // 4. multipart 续算 == 一次算完
    {
        std::uint32_t part = CRC::Calculate(CHECK_DATA, 4, CRC::CRC_32());
        part = CRC::Calculate(CHECK_DATA + 4, CHECK_SIZE - 4, CRC::CRC_32(), part);
        Check("CRC-32 multipart(4+5) == full", part, 0xCBF43926ull);
    }

    // 5. CRC-32/MPEG-2（final XOR 与 reflect 组合不同）
    Check("CRC-32/MPEG-2",
          CRC::Calculate(CHECK_DATA, CHECK_SIZE, CRC::CRC_32_MPEG2()), 0x0376E6E7ull);

    // 6/7. CRC-16/CCITT-FALSE：逐位与查表
    Check("CRC-16/CCITT-FALSE bitwise",
          CRC::Calculate(CHECK_DATA, CHECK_SIZE, CRC::CRC_16_CCITTFALSE()), 0x29B1ull);
    {
        CRC::Table<std::uint16_t, 16> table(CRC::CRC_16_CCITTFALSE());
        Check("CRC-16/CCITT-FALSE table",
              CRC::Calculate(CHECK_DATA, CHECK_SIZE, table), 0x29B1ull);
    }

    // 8. CRC-16/KERMIT（输入输出双向反射）
    Check("CRC-16/KERMIT",
          CRC::Calculate(CHECK_DATA, CHECK_SIZE, CRC::CRC_16_KERMIT()), 0x2189ull);

    // 9. CRC-8
    Check("CRC-8", CRC::Calculate(CHECK_DATA, CHECK_SIZE, CRC::CRC_8()), 0xF4ull);

    // 10. CRC-64（esoteric 定义区）
    Check("CRC-64",
          CRC::Calculate(CHECK_DATA, CHECK_SIZE, CRC::CRC_64()), 0x6C40DF5F0B497347ull);

    // 11/12. 非 8 位整倍数输入（USB 2.0 的 5-bit CRC 覆盖 11 位数据）
    {
        static const unsigned char USB_DATA[] = {0x10, 0x07};
        Check("CRC-5/USB 11-bit bitwise (CalculateBits)",
              CRC::CalculateBits(USB_DATA, 11, CRC::CRC_5_USB()), 0x05ull);
        CRC::Table<std::uint8_t, 5> table(CRC::CRC_5_USB());
        Check("CRC-5/USB 11-bit table (CalculateBits)",
              CRC::CalculateBits(USB_DATA, 11, table), 0x05ull);
    }

    // 13. 参数结构体字段（反射/多项式可被消费者读取）
    Check("CRC-32 parameters.polynomial == 0x04C11DB7",
          CRC::CRC_32().polynomial, 0x04C11DB7ull);

    std::printf("[consumer] summary: %d/%d assertions passed "
                "(runtime), compile-time static_assert=1\n",
                g_total - g_failed, g_total);
    return g_failed == 0 ? 0 : 1;
}
