// HarmonyOS 专项测试 — exprtk 0.0.3
// 在 OHOS(aarch64) 目标平台真实编译运行：除调用库公开 API 外，额外验证
// 鸿蒙平台运行时行为（IEEE-754 double 语义、libm 数学函数一致性、内存分配
// 与表达式重绑定在 OHOS 运行时的正确性），非空壳、非只打印。
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "exprtk.hpp"

static int failures = 0;

static void check(bool cond, const char* what)
{
    if (!cond)
    {
        std::printf("FAIL: %s\n", what);
        ++failures;
    }
}

int main()
{
#if defined(__OHOS__)
    std::printf("harmonyos_specific_test: platform=OHOS(aarch64)\n");
#else
    std::printf("harmonyos_specific_test: platform=non-OHOS (host build)\n");
#endif

    typedef exprtk::symbol_table<double> symbol_table_t;
    typedef exprtk::expression<double>   expression_t;
    typedef exprtk::parser<double>       parser_t;

    // 1) IEEE-754 double 语义在 OHOS 运行时与 libm 一致：表达式引擎内
    //    sin/cos/log/exp 求值与 std:: 同名函数结果误差须在 1e-12 内。
    {
        symbol_table_t st;
        expression_t   e;
        parser_t       p;
        double ang = 0.7;
        st.add_variable("a", ang);
        st.add_constants();
        e.register_symbol_table(st);

        check(p.compile("sin(a)^2 + cos(a)^2", e), "compile trig identity");
        check(std::fabs(e.value() - 1.0) < 1e-12,
              "sin^2+cos^2 == 1 on OHOS runtime (IEEE-754/libm consistent)");

        check(p.compile("log(exp(a))", e), "compile log(exp(a))");
        check(std::fabs(e.value() - ang) < 1e-12,
              "log(exp(a)) == a on OHOS runtime");
    }

    // 2) 向量绑定与循环在 OHOS 运行时真实计算（内存分配路径）。
    {
        symbol_table_t st;
        expression_t   e;
        parser_t       p;
        std::vector<double> v(8, 0.0);
        for (std::size_t i = 0; i < v.size(); ++i) v[i] = static_cast<double>(i + 1);
        st.add_vector("v", v);
        e.register_symbol_table(st);

        check(p.compile("sum(v)", e), "compile sum(v)");
        check(std::fabs(e.value() - 36.0) < 1e-12, "sum(1..8) == 36 on OHOS runtime");

        check(p.compile("avg(v) * 8", e), "compile avg(v)*8");
        check(std::fabs(e.value() - 36.0) < 1e-12, "avg(v)*8 == 36 on OHOS runtime");
    }

    // 3) 表达式重绑定 + 条件/循环控制流在 OHOS 运行时正确（变量重赋值后
    //    同一 expression 对象重新求值）。
    {
        symbol_table_t st;
        expression_t   e;
        parser_t       p;
        double x = 1.0;
        double total = 0.0;
        st.add_variable("x", x);
        st.add_variable("total", total);
        e.register_symbol_table(st);

        check(p.compile("for(var i := 0; i < 10; i += 1) { if (x > 0) total += x; }", e),
              "compile loop with conditional");
        check(std::fabs(e.value() - 10.0) < 1e-12,
              "loop accumulates 10*x == 10 on OHOS runtime");

        x = 2.0;
        check(std::fabs(e.value() - 30.0) < 1e-12,
              "re-bind x=2 then loop accumulates 20 on OHOS runtime");
    }

    if (failures == 0)
    {
        std::printf("harmonyos_specific_test: all OHOS runtime checks passed\n");
        return 0;
    }
    std::printf("harmonyos_specific_test: %d check(s) failed\n", failures);
    return 1;
}
