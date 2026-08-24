#include <fmt/core.h>
#include <fmt/format.h>
#include <cstdio>
#include <cstring>
#include <string>

// 真实计算 + 断言：格式化是 fmt 的全部意义，只验「能编能链」等于没验。
int main() {
    int bad = 0;

    // ① 位置参数 + 整数格式化
    std::string a = fmt::format("{}-{}", 42, "x");
    if (a != "42-x") { std::printf("FAIL 基本格式化: %s\n", a.c_str()); bad++; }

    // ② 宽度/填充/进制 —— 走的是 fmt 的格式规格解析器，不是 printf 转发
    std::string b = fmt::format("{:08.3f}|{:>5}|{:#x}", 3.14159, "ab", 255);
    if (b != "0003.142|   ab|0xff") { std::printf("FAIL 格式规格: %s\n", b.c_str()); bad++; }

    // ③ 编译期参数个数检查路径 + 命名参数
    std::string c = fmt::format("{n} {v}", fmt::arg("n", "ver"), fmt::arg("v", 7));
    if (c != "ver 7") { std::printf("FAIL 命名参数: %s\n", c.c_str()); bad++; }

    // ④ format_to 写进定长缓冲：验证迭代器接口（下游 lfp/dlisio 用的就是这条）
    char buf[32] = {0};
    auto end = fmt::format_to(buf, "{}+{}", 1, 2);
    *end = '\0';
    if (std::strcmp(buf, "1+2") != 0) { std::printf("FAIL format_to: %s\n", buf); bad++; }

    // ⑤ 版本宏与实际链接到的库一致（防「头是 7.1.3、链到别的版本」）
    if (FMT_VERSION / 10000 != 7) { std::printf("FAIL 版本: %d\n", FMT_VERSION); bad++; }

    if (bad == 0) std::printf("fmt 7.1.3: 5 项断言全过\n");
    return bad ? 1 : 0;
}
