// Conan test_package for kiwisolver — real API usage (R34, no empty shell).
//
// Compiles against the packaged <kiwi/kiwi.h> headers and actually solves a
// small constraint system with kiwi::Solver, asserting the solution values.
// Mirrors the canonical upstream README example (x + y == 10, x - y == 4
//  => x == 7, y == 3), plus an additional inequality/strength check.
#include <kiwi/kiwi.h>

#include <cstdio>
#include <cmath>

int main() {
    // 1) canonical example: two equations, two unknowns
    kiwi::Solver solver;
    kiwi::Variable x("x");
    kiwi::Variable y("y");
    solver.addConstraint(x + y == 10);
    solver.addConstraint(x - y == 4);
    solver.updateVariables();

    if (std::abs(x.value() - 7.0) > 1e-9 || std::abs(y.value() - 3.0) > 1e-9) {
        std::fprintf(stderr, "FAIL: expected x=7, y=3, got x=%g, y=%g\n",
                     x.value(), y.value());
        return 1;
    }
    std::printf("OK: solved x=7, y=3 (x=%g, y=%g)\n", x.value(), y.value());

    // 2) inequality + edit variables (strength/priority path)
    kiwi::Solver solver2;
    kiwi::Variable a("a");
    kiwi::Variable b("b");
    solver2.addConstraint(a >= 0);
    solver2.addConstraint(b >= 0);
    solver2.addConstraint(a + b == 1);
    solver2.addEditVariable(a, kiwi::strength::strong);
    solver2.addEditVariable(b, kiwi::strength::strong);
    solver2.suggestValue(a, 0.25);
    solver2.suggestValue(b, 0.75);
    solver2.updateVariables();
    if (std::abs(a.value() - 0.25) > 1e-9 || std::abs(b.value() - 0.75) > 1e-9) {
        std::fprintf(stderr, "FAIL: edit-var suggestion mismatch a=%g b=%g\n",
                     a.value(), b.value());
        return 1;
    }
    std::printf("OK: edit variables honored (a=%g, b=%g)\n",
                a.value(), b.value());

    std::printf("kiwisolver test_package: all API checks passed\n");
    return 0;
}
