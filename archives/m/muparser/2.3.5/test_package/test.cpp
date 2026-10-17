#include <muParser.h>
#include <cstdio>
#include <cmath>

// R34: test_package 必须实质调用被测包 API，禁止空壳只打印字符串。
int main()
{
    int failures = 0;
    try {
        mu::Parser p;
        p.SetExpr("1+2*3");
        double v = p.Eval();
        std::printf("muparser test: 1+2*3 = %f\n", v);
        if (std::fabs(v - 7.0) > 1e-9) { std::printf("FAIL: expected 7\n"); failures++; }

        p.SetExpr("sin(0)+cos(0)");
        v = p.Eval();
        std::printf("muparser test: sin(0)+cos(0) = %f\n", v);
        if (std::fabs(v - 1.0) > 1e-9) { std::printf("FAIL: expected 1\n"); failures++; }

        mu::value_type x = 4.0;
        p.DefineVar("x", &x);
        p.SetExpr("sqrt(x)");
        v = p.Eval();
        std::printf("muparser test: sqrt(4) = %f\n", v);
        if (std::fabs(v - 2.0) > 1e-9) { std::printf("FAIL: expected 2\n"); failures++; }
    } catch (mu::Parser::exception_type& e) {
        std::printf("muparser test FAILED with exception: %s\n", e.GetMsg().c_str());
        return 1;
    }

    if (failures == 0) {
        std::printf("muparser test: ALL PASS\n");
        return 0;
    }
    std::printf("muparser test: %d failure(s)\n", failures);
    return failures;
}
