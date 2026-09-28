// HarmonyOS 专项测试 — crossguid/0.2.2
// 验证适配后的库在 OHOS (aarch64, clang15/libc++) 上的真实运行行为：
// 批量生成唯一性、字节数组<->字符串往返、swap/拷贝语义、错误输入处理、
// 规范 UUID 字符串格式。仅使用安装的公开头文件与公开 API。
#include "Guid.hpp"
#include <array>
#include <cctype>
#include <iostream>
#include <set>
#include <sstream>
#include <string>

namespace {

bool isHex(char c)
{
    return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
}

// 校验 8-4-4-4-12 规范格式
bool isCanonicalUuidString(const std::string &s)
{
    if (s.size() != 36)
        return false;
    for (size_t i = 0; i < 36; ++i) {
        if (i == 8 || i == 13 || i == 18 || i == 23) {
            if (s[i] != '-')
                return false;
        } else if (!isHex(s[i])) {
            return false;
        }
    }
    return true;
}

} // namespace

int main()
{
    int failed = 0;

    // 1) 批量生成 1000 个 GUID，全部唯一且字符串格式规范（真实运行行为压力验证）
    std::set<std::string> seen;
    for (int i = 0; i < 1000; ++i) {
        xg::Guid g = xg::newGuid();
        std::string s = g.str();
        if (!isCanonicalUuidString(s)) {
            std::cerr << "FAIL: non-canonical uuid string: " << s << std::endl;
            ++failed;
            break;
        }
        if (!seen.insert(s).second) {
            std::cerr << "FAIL: duplicate guid generated: " << s << std::endl;
            ++failed;
            break;
        }
    }
    if (failed == 0)
        std::cout << "1000 generated guids unique + canonical format" << std::endl;

    // 2) 字节数组构造：0x00..0xFF 递增 16 字节，字符串往返一致
    {
        std::array<unsigned char, 16> bytes;
        for (int i = 0; i < 16; ++i)
            bytes[i] = static_cast<unsigned char>(i);
        xg::Guid fromBytes(bytes);
        std::stringstream ss;
        ss << fromBytes;
        xg::Guid fromString(ss.str());
        if (!(fromBytes == fromString) || ss.str().size() != 36) {
            std::cerr << "FAIL: bytes<->string round trip: " << ss.str() << std::endl;
            ++failed;
        } else {
            std::cout << "bytes<->string round trip ok: " << ss.str() << std::endl;
        }
    }

    // 3) swap / 拷贝赋值语义
    {
        xg::Guid a = xg::newGuid();
        xg::Guid b = xg::newGuid();
        std::string sa = a.str();
        std::string sb = b.str();
        a.swap(b);
        if (a.str() != sb || b.str() != sa) {
            std::cerr << "FAIL: swap semantics" << std::endl;
            ++failed;
        } else {
            std::cout << "swap/copy semantics ok" << std::endl;
        }
    }

    // 4) 错误输入处理：空串 / 非法字符 / 长度不符 → isValid()==false 且等于空 Guid
    {
        xg::Guid empty;
        int bad = 0;
        const char *badInputs[] = {
            "", "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz",
            "7bcd757f-5b10-4f9b-af69", "7bcd757f-5b10-4f9b-af69-1a1f226f3b3e!",
        };
        for (const char *in : badInputs) {
            xg::Guid g(in);
            if (g != empty || g.isValid()) {
                ++bad;
            }
        }
        if (bad != 0) {
            std::cerr << "FAIL: invalid inputs accepted (" << bad << ")" << std::endl;
            ++failed;
        } else {
            std::cout << "invalid-input handling ok" << std::endl;
        }
    }

    if (failed != 0) {
        std::cerr << failed << " ohos-specific checks failed." << std::endl;
        return 1;
    }
    std::cout << "All ohos-specific tests passed!" << std::endl;
    return 0;
}