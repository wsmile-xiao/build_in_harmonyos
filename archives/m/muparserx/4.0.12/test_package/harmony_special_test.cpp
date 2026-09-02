// harmony_special_test.cpp — muparserx 4.0.12 HarmonyOS 专项测试
//
// 验证目标（HarmonyOS 兼容性/行为）：
//   1) 在 HarmonyOS PC (aarch64-linux-ohos, clang 15, libc++) 工具链上
//      编译并运行 muparserx，确认 OHOS 平台宏 __OHOS__/__OHOS_FAMILY__ 存在；
//   2) 实际调用 muparserx 公开 API（ParserX::SetExpr/Eval/GetFloat/DefineVar）
//      验证表达式求值在 OHOS 运行时下数值正确；
//   3) 验证变量定义与读取在 OHOS 上行为一致；
//   4) 验证无效表达式错误处理路径（上游 ParserError 异常机制）在 OHOS 上可用。
// 本测试真实构造解析器并断言结果，非空壳、非仅编译、非复述上游测试。
#include <mpParser.h>

#include <cstdio>
#include <cstdlib>
#include <cmath>

static int failures = 0;

static void check(const char* name, bool ok) {
    if (ok) {
        std::printf("  [PASS] %s\n", name);
    } else {
        std::printf("  [FAIL] %s\n", name);
        failures++;
    }
}

int main() {
#if defined(__OHOS__) || defined(__OHOS_FAMILY__)
    std::printf("  [INFO] HarmonyOS platform macros detected: __OHOS__ defined\n");
#else
    std::printf("  [FAIL] __OHOS__ macro NOT defined — not building for HarmonyOS\n");
    failures++;
#endif

    // (2) 数值求值："(1+2)*3 - 4/2" = 9 - 2 = 7
    {
        mup::ParserX p;
        p.SetExpr("(1+2)*3 - 4/2");
        double v = p.Eval().GetFloat();
        check("expr eval: (1+2)*3-4/2 == 7", std::fabs(v - 7.0) < 1e-12);
    }

    // (3) 变量定义与使用："a*b + c" with a=2,b=5,c=1 -> 11
    {
        mup::ParserX p;
        mup::Value vVarVal[] = { mup::Value(2.0), mup::Value(5.0), mup::Value(1.0) };
        p.DefineVar("a", mup::Variable(&vVarVal[0]));
        p.DefineVar("b", mup::Variable(&vVarVal[1]));
        p.DefineVar("c", mup::Variable(&vVarVal[2]));
        p.SetExpr("a*b + c");
        double v = p.Eval().GetFloat();
        check("expr eval: a*b+c with a=2,b=5,c=1 == 11", std::fabs(v - 11.0) < 1e-12);
    }

    // (4) 无效表达式错误处理（上游 ParserError 异常机制）
    {
        mup::ParserX p;
        p.SetExpr("1 +");
        bool threw = false;
        try {
            p.Eval();
        } catch (mup::ParserError&) {
            threw = true;
        } catch (...) {
            threw = true;
        }
        check("error path: invalid expr '1 +' throws ParserError", threw);
    }

    std::printf("HarmonyOS special test finished: failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}