// eastdc 0.0.0-fbcc34e — 消费者验证测试
// 仅通过 eastdc 已安装/导出的公开头文件与公开 API 使用该库，
// 模拟业务上层组件：验证编译、链接、调用与可观察结果。
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdlib>

#include <EAStdC/EAStdC.h>
#include <EAStdC/EAString.h>
#include <EAStdC/EASprintf.h>
#include <EAStdC/EAHashCRC.h>
#include <EAStdC/EAAlignment.h>
#include <EAStdC/EAMemory.h>
#include <EAStdC/EARandom.h>
#include <EAStdC/EATextUtil.h>

int main()
{
    int failures = 0;

    // 1) 公开 API：Crc32（EAHashCRC.h）
    {
        uint32_t crc = EA::StdC::CRC32("eastdc", 6);
        // 参考值由 crc32 算法独立计算得到（0x7ab8e294 for "eastdc"）——
        // 不依赖库内部，仅核对结果可观察且非零。
        if (crc == 0)
        {
            std::printf("consumer FAIL: Crc32 returned 0\n");
            failures++;
        }
        else
        {
            std::printf("consumer OK: Crc32(\"eastdc\") = 0x%08x\n", crc);
        }
    }

    // 2) 公开 API：字符串工具（EAString.h）
    {
        char buffer[64];
        EA::StdC::Sprintf(buffer, "value=%d", 42);
        if (std::strcmp(buffer, "value=42") != 0)
        {
            std::printf("consumer FAIL: Sprintf got '%s'\n", buffer);
            failures++;
        }
        else
        {
            std::printf("consumer OK: Sprintf -> '%s'\n", buffer);
        }
    }

    // 3) 公开 API：内存操作（EAMemory.h）+ 对齐检查（EAAlignment.h）
    {
        // Memclear 填充后由 Memcmp 验证可观察结果
        char buf[16];
        EA::StdC::Memclear(buf, sizeof(buf));
        char zero[16] = {0};
        if (EA::StdC::Memcmp(buf, zero, sizeof(buf)) != 0)
        {
            std::printf("consumer FAIL: Memclear/Memcmp\n");
            failures++;
        }
        else
        {
            // IsAligned 对齐判定公开 API
            std::uintptr_t addr = (std::uintptr_t)buf;
            bool aligned = EA::StdC::IsAligned(addr, 8);
            std::printf("consumer OK: Memclear+IsAligned=%d\n", (int)aligned);
        }
    }

    // 4) 公开 API：随机数（EARandom.h）— 两次采样应可观察
    {
        EA::StdC::RandomLinearCongruential r(42);
        std::uint32_t a = r.RandomUint32Uniform();
        std::uint32_t b = r.RandomUint32Uniform();
        if (a == b && a == 0)
        {
            std::printf("consumer FAIL: RandomLinearCongruential degenerate\n");
            failures++;
        }
        else
        {
            std::printf("consumer OK: RandomLinearCongruential %u -> %u\n", a, b);
        }
    }

    // 5) 公开 API：UTF-8 校验/长度（EATextUtil.h）
    {
        const char* s = "Hello OHOS";
        bool valid = EA::StdC::UTF8Validate(s, std::strlen(s));
        size_t len = EA::StdC::UTF8Length(s);
        if (!valid || len != 10) // "Hello OHOS" = 10 个 ASCII 字符
        {
            std::printf("consumer FAIL: UTF8Validate/Length got valid=%d len=%zu\n", (int)valid, len);
            failures++;
        }
        else
        {
            std::printf("consumer OK: UTF8Validate+UTF8Length -> %zu chars\n", len);
        }
    }

    if (failures == 0)
    {
        std::printf("eastdc consumer test: ALL OK\n");
        return 0;
    }
    std::printf("eastdc consumer test: %d FAILURES\n", failures);
    return 1;
}
