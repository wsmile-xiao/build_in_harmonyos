#include <libaegisub/util.h>

#include <cstdio>

// R34 非空壳测试：真实 include + 链接 + 调用 libaegisub 核心库 API。
// agi::util::try_parse 是 libaegisub 的字符串解析函数，测试其 OHOS 上可链接可运行。
int main() {
    double d = 0.0;
    int i = 0;
    bool ok_d = agi::util::try_parse("123.456", &d);
    bool ok_i = agi::util::try_parse("42", &i);
    if (!ok_d || !ok_i) {
        std::printf("FAIL: try_parse failed\n");
        return 1;
    }
    // 断言解析结果
    if (d != 123.456 || i != 42) {
        std::printf("FAIL: try_parse wrong value d=%f i=%d\n", d, i);
        return 1;
    }
    std::printf("OK: agi::util::try_parse linked and ran (d=%f, i=%d)\n", d, i);
    return 0;
}
