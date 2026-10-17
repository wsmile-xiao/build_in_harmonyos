// L1 消费者测试: 对 libyate 编译+链接+String API 行为调用（R34 实质依赖）
// API 依据: yateclass.h String 类 (String(const char*, int) / c_str() / length())
#include <yatephone.h>
#include <cstring>
#include <iostream>

using namespace TelEngine;

int main()
{
    // 断言 1a: String 构造 + length()（"yate-ohos-test" = 14 字符）
    String s("yate-ohos-test");
    if (s.length() != 14) {
        std::cerr << "FAIL: String length != 14" << std::endl;
        return 1;
    }
    // 断言 1b: String 内容一致性 (c_str())
    if (std::strcmp(s.c_str(), "yate-ohos-test") != 0) {
        std::cerr << "FAIL: String content mismatch" << std::endl;
        return 2;
    }
    std::cout << "PASS: yate C++ API OK: " << s.c_str() << std::endl;
    return 0;
}
