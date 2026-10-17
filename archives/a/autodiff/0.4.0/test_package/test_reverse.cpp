// autodiff library — consumer test for autodiff/0.4.0 (reverse mode)
//
// Verifies that autodiff reverse mode can be included and basic APIs work:
//   - autodiff::var (derivative via derivatives())
//
// Uses explicit CHECK macros instead of assert() so validation works in
// both Debug and Release builds.

#include <cmath>
#include <cstdlib>
#include <iostream>

#include <autodiff/reverse.hpp>

#define CHECK(expr)                                                      \
    do {                                                                 \
        if (!(expr)) {                                                   \
            std::cerr << "FAIL: " << __FILE__ << ":" << __LINE__ << ": " \
                      << #expr << std::endl;                             \
            std::exit(1);                                                \
        }                                                                \
    } while (0)

int main()
{
    // Convenience lambda: grad(y,x) = dy/dx (mirrors upstream test pattern)
    auto grad = [](const autodiff::var& y, const autodiff::var& x) -> double {
        return autodiff::derivatives(y)(x);
    };

    // Test 1: var type basic arithmetic
    autodiff::var a = 10;
    autodiff::var b = 20;
    CHECK(autodiff::val(a) == 10.0);
    CHECK(autodiff::val(b) == 20.0);
    CHECK(autodiff::val(a + b) == 30.0);
    CHECK(autodiff::val(a * b) == 200.0);
    CHECK(autodiff::val(b - a) == 10.0);
    CHECK(autodiff::val(b / a) == 2.0);
    std::cout << "PASS: reverse mode — basic arithmetic OK" << std::endl;

    // Test 2: first-order derivatives
    autodiff::var c = a + b;
    CHECK(std::fabs(grad(c, a) - 1.0) < 1e-10);
    CHECK(std::fabs(grad(c, b) - 1.0) < 1e-10);

    autodiff::var d = a * b;
    CHECK(std::fabs(grad(d, a) - 20.0) < 1e-10);
    CHECK(std::fabs(grad(d, b) - 10.0) < 1e-10);

    autodiff::var e = b - a;
    CHECK(std::fabs(grad(e, a) - (-1.0)) < 1e-10);
    CHECK(std::fabs(grad(e, b) - 1.0) < 1e-10);
    std::cout << "PASS: reverse mode — derivatives OK" << std::endl;

    // Test 3: math functions
    autodiff::var x = 0.5;
    autodiff::var s = sin(x);
    CHECK(std::fabs(autodiff::val(s) - std::sin(0.5)) < 1e-10);
    CHECK(std::fabs(grad(s, x) - std::cos(0.5)) < 1e-10);

    autodiff::var ex = exp(x);
    CHECK(std::fabs(autodiff::val(ex) - std::exp(0.5)) < 1e-10);
    CHECK(std::fabs(grad(ex, x) - std::exp(0.5)) < 1e-10);

    autodiff::var l = log(x);
    CHECK(std::fabs(autodiff::val(l) - std::log(0.5)) < 1e-10);
    CHECK(std::fabs(grad(l, x) - 2.0) < 1e-10);
    std::cout << "PASS: reverse mode — math functions OK" << std::endl;

    // Test 4: composite expression f = x^2 + x*y + y^2
    autodiff::var x2 = 2.0;
    autodiff::var y2 = 3.0;
    autodiff::var f = x2*x2 + x2*y2 + y2*y2;
    CHECK(std::fabs(autodiff::val(f) - 19.0) < 1e-10);
    CHECK(std::fabs(grad(f, x2) - 7.0) < 1e-10);
    CHECK(std::fabs(grad(f, y2) - 8.0) < 1e-10);
    std::cout << "PASS: reverse mode — composite expression OK" << std::endl;

    std::cout << std::endl << "All autodiff reverse-mode consumer tests PASSED." << std::endl;
    return 0;
}
