// test_package.cpp — muparserx 4.0.12 consumer smoke test (HarmonyOS PC).
// Exercises the real muparserx API: expression parse + evaluation.
#include <mpParser.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>

int main()
{
    mup::ParserX parser;
    parser.SetExpr("1 + 2 * 3 - 4");
    double val = parser.Eval().GetFloat();
    if (std::fabs(val - 3.0) > 1e-12) {
        std::printf("FAIL: 1+2*3-4 = %f (expected 3)\n", val);
        return 1;
    }
    std::printf("PASS: 1+2*3-4 = %f\n", val);
    return 0;
}
