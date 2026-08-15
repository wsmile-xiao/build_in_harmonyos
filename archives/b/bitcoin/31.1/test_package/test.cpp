#include <cstdio>
#include <string>
#include <vector>

/* 消费者编译/链接验证：
 * 1. 校验 CLIENT_VERSION_* 版本宏（头文件可消费）；
 * 2. 构造 uint256 并检查 IsNull()（真实类型/头文件可用性）；
 * 3. 调用 ParseHex（定义于 libbitcoin_util 的 strencodings.cpp，真实链接符号），
 *    验证静态库可链接且运行行为正确，而非仅比对恒真的头文件版本宏。
 */
#include <clientversion.h>
#include <uint256.h>
#include <util/strencodings.h>

int main()
{
    // 1) 版本宏（头文件消费验证）
    std::printf("bitcoin client version: %d.%d.%d\n",
                CLIENT_VERSION_MAJOR, CLIENT_VERSION_MINOR, CLIENT_VERSION_BUILD);
    std::printf("expected version: 31.1.0\n");

    if (CLIENT_VERSION_MAJOR != 31 || CLIENT_VERSION_MINOR != 1) {
        std::fprintf(stderr, "ERROR: version mismatch!\n");
        return 1;
    }

    // 2) 真实库符号：构造 uint256 并检查 IsNull()（R34 真实链接验证）
    const uint256 null_hash;
    if (!null_hash.IsNull()) {
        std::fprintf(stderr, "ERROR: default-constructed uint256 should be null\n");
        return 1;
    }

    // 3) 真实库符号：调用 ParseHex（libbitcoin_util 的 strencodings.cpp 导出，
    //    TryParseHex<uint8_t> 显式实例化；链接失败或行为错误即报错）
    const std::vector<uint8_t> parsed = ParseHex("00ff10");
    if (parsed.size() != 3 || parsed[0] != 0x00 || parsed[1] != 0xff || parsed[2] != 0x10) {
        std::fprintf(stderr, "ERROR: ParseHex returned wrong bytes\n");
        return 1;
    }

    std::printf("test bitcoin 31.1: OK\n");
    return 0;
}
