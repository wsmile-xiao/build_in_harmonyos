// HarmonyOS 专项测试 — univalue 1.1.1
//
// 目的（任务 univalue-1.1.1-r01-pc1-30 第 5 步要求）：
//   - 验证本包确实编译并运行在 HarmonyOS PC (aarch64-linux-ohos) 目标上；
//   - 验证 univalue 库在本平台的真实可用性（链接 + JSON 读写运行）。
// 本文件编译时依赖 __OHOS__ 宏（OHOS SDK 默认定义），并调用 libunivalue 的
// 公开 API 做 JSON 往返解析，任何一步失败都会使 CTest 退出码非 0。
#include <univalue.h>

#include <cstdio>
#include <string>

#ifndef __OHOS__
#error "HarmonyOS special test requires __OHOS__ to be defined (wrong target?)"
#endif

static int failures = 0;

static void expect(bool cond, const char* what) {
    if (!cond) {
        std::printf("FAIL: %s\n", what);
        failures++;
    } else {
        std::printf("PASS: %s\n", what);
    }
}

int main() {
    // 1) 平台断言：必须在 OHOS 目标上编译（__OHOS__ 已由 #ifndef 强制）。
    expect(true, "compiled for HarmonyOS (__OHOS__ defined)");

    // 2) 库真实可用性：与 test_package 消费者测试互补，这里验证对象构造、
    //    数组/对象嵌套、转义字符串与数字往返。
    UniValue doc;
    const char* json =
        "{\"answer\":42,\"list\":[1,\"two\",3.0],\"esc\":\"a\\u0000b\"}";
    expect(doc.read(json), "parse nested JSON on OHOS");

    UniValue list = doc["list"];
    expect(list.isArray(), "'list' is an array");
    expect(list.size() == 3, "'list' has 3 elements");
    expect(list[1].getValStr() == "two", "array string element round-trip");

    UniValue esc = doc["esc"];
    std::string expected("a");
    expected.push_back('\0');
    expected.push_back('b');
    expect(esc.getValStr() == expected, "escaped NUL string round-trip");

    // 3) 序列化往返：write() 后重新 read() 必须保持语义等价。
    std::string written = doc.write();
    UniValue reparsed;
    expect(reparsed.read(written), "re-parse serialized output");
    expect(reparsed.isObject(), "reparsed value is an object");
    expect(reparsed["answer"].getValStr() == "42", "integer value preserved");

    // 4) 类型安全 getter 在本平台同样按规范抛异常。
    bool threw = false;
    try {
        (void)list[0].get_str();  // 数字 1 按字符串访问应抛 runtime_error
    } catch (const std::runtime_error&) {
        threw = true;
    }
    expect(threw, "type-safe getter throws on wrong type");

    if (failures == 0) {
        std::printf("ohos_special_test: all HarmonyOS checks passed\n");
        return 0;
    }
    std::printf("ohos_special_test: %d check(s) failed\n", failures);
    return 1;
}
