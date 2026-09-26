// Consumer test for the packaged seexpr library (see test_package/conanfile.py
// for the A1/A2/A3 check inventory). A3 is implemented by this program.
#include <cstdio>

#include <SeExpr2/Expression.h>

using namespace SeExpr2;

namespace {

struct SimpleExpression : public Expression {
    struct Var : public ExprVarRef {
        double value = 0.0;
        Var() : ExprVarRef(ExprType().FP(1).Varying()) {}
        void eval(double* result) { result[0] = value; }
        void eval(const char**) {}
    };
    mutable Var x;

    ExprVarRef* resolveVar(const std::string& name) const {
        if (name == "x") return &x;
        return nullptr;
    }

    explicit SimpleExpression(const std::string& str) : Expression(str) {}
};

int failures = 0;

void check(bool ok, const char* what) {
    std::printf("%s: %s\n", ok ? "PASS" : "FAIL", what);
    if (!ok) failures++;
}

}  // namespace

int main() {
    // Consumer smoke: constant folding through the packaged library.
    Expression constant("3+4");
    check(constant.isValid() && constant.isConstant() && constant.evalFP()[0] == 7,
          "constant expression 3+4 evaluates to 7");

    // Consumer smoke: variable resolution through the packaged library.
    SimpleExpression varExpr("$x*2+1");
    varExpr.x.value = 3.0;
    check(varExpr.isValid() && varExpr.evalFP()[0] == 7,
          "variable expression $x*2+1 with x=3 evaluates to 7");

    // A3 (HarmonyOS-specific): on aarch64 OHOS the library is built with
    // ENABLE_SSE4=OFF, so noise() takes the portable (#ifndef __SSE4_1__)
    // path in Noise.cpp. It must stay deterministic and in the documented
    // [0,1] range of the noise() builtin.
    SimpleExpression noiseExpr("noise($x, 2.5, 3.75)");
    noiseExpr.x.value = 1.25;
    check(noiseExpr.isValid(), "noise expression is valid");
    const double first = noiseExpr.evalFP()[0];
    const double second = noiseExpr.evalFP()[0];
    check(first == second, "portable noise path is deterministic across evaluations");
    check(first >= 0.0 && first <= 1.0, "noise() result within [0,1]");

    if (failures) {
        std::printf("test_seexpr: %d check(s) FAILED\n", failures);
        return 1;
    }
    std::printf("test_seexpr: all checks passed\n");
    return 0;
}
