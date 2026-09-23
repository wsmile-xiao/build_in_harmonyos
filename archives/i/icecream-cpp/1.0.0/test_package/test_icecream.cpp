// test_package 消费者测试：真实调用被测库 icecream-cpp 的 API（R34）。
// 同时包含 HarmonyOS 专项断言：OHOS libc（musl 系）对 %p 空指针输出 "0"，
// glibc 输出 "(nil)"——该差异为平台 libc 行为，与上游测试适配说明一致。
#include <icecream.hpp>

#include <cstdio>
#include <string>

int main()
{
    int failures = 0;

    // 消费者功能验证：IC() 输出捕获到 std::string
    {
        IC_CONFIG_SCOPE();
        std::string str;
        IC_CONFIG.output(str);

        const int v = 42;
        IC(v);

        const std::string expect = "ic| v: 42\n";
        if (str != expect) {
            std::fprintf(stderr, "FAIL: got '%s' expected '%s'\n", str.c_str(), expect.c_str());
            ++failures;
        } else {
            std::printf("consumer ok: %s", str.c_str());
        }
    }
    // IC 表达式与多个参数
    {
        IC_CONFIG_SCOPE();
        std::string str;
        IC_CONFIG.output(str);

        const int a = 1;
        const int b = 2;
        IC(a, b);
        IC(a + b);

        if (str.find("a") == std::string::npos || str.find("b") == std::string::npos) {
            std::fprintf(stderr, "FAIL: multi-arg output missing names: '%s'\n", str.c_str());
            ++failures;
        } else {
            std::printf("multi-arg ok\n");
        }
    }
    // HarmonyOS 专项：空指针 %p 输出格式（平台 libc 行为断言，带实质逻辑）
    {
        IC_CONFIG_SCOPE();
        std::string str;
        IC_CONFIG.output(str);

        int* p = nullptr;
        IC(p);

#if defined(__OHOS__)
        // OHOS 工具链（libc++ + OHOS libc）：%p 空指针输出 "0"
        const std::string expect_ohos = "ic| p: 0\n";
        if (str != expect_ohos) {
            std::fprintf(stderr, "FAIL(ohos): got '%s' expected '%s'\n", str.c_str(), expect_ohos.c_str());
            ++failures;
        } else {
            std::printf("ohos nullptr %%p format ok: %s", str.c_str());
        }
#else
        // 其他平台（glibc 系）：接受 "(nil)" 或 0x0 形式
        if (str.find("nil") == std::string::npos && str.find("0x0") == std::string::npos &&
            str.find("0\n") == std::string::npos) {
            std::fprintf(stderr, "FAIL(platform): unexpected output: '%s'\n", str.c_str());
            ++failures;
        } else {
            std::printf("platform nullptr %%p format ok\n");
        }
#endif
    }

    if (failures == 0) {
        std::printf("ALL test_package checks passed\n");
        return 0;
    }
    return 1;
}