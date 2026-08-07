// autodiff library — consumer test for autodiff/0.4.0 (forward mode)
//
// Verifies that autodiff forward mode can be included and basic APIs work:
//   - autodiff::forward::dual (derivative via derivative())
//
// Uses explicit CHECK macros instead of assert() so validation works in
// both Debug and Release builds.

#include <cmath>
#include <cstdlib>
#include <iostream>

#include <autodiff/forward.hpp>

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
    using namespace autodiff;
    using namespace autodiff::forward;

    // Test 1: dual type basic arithmetic
    dual x = 100;
    dual y = 10;
    CHECK(val(x) == 100.0);
    CHECK(val(y) == 10.0);
    CHECK(val(x + y) == 110.0);
    CHECK(val(x - y) == 90.0);
    CHECK(val(x * y) == 1000.0);
    CHECK(val(x / y) == 10.0);
    std::cout << "PASS: forward mode — basic arithmetic OK" << std::endl;

    // Test 2: derivative of x^2
    x = 2.0;
    auto f1 = [](dual a) -> dual { return a * a; };
    CHECK(std::fabs(val(f1(x)) - 4.0) < 1e-10);
    CHECK(std::fabs(derivative(f1, wrt(x), x) - 4.0) < 1e-10);
    std::cout << "PASS: forward mode — derivative x^2 OK" << std::endl;

    // Test 3: derivative of x^3
    auto f2 = [](dual a) -> dual { return a * a * a; };
    CHECK(std::fabs(val(f2(x)) - 8.0) < 1e-10);
    CHECK(std::fabs(derivative(f2, wrt(x), x) - 12.0) < 1e-10);
    std::cout << "PASS: forward mode — derivative x^3 OK" << std::endl;

    // Test 4: sin(x) derivative
    dual z = 1.0;
    auto f3 = [](dual a) -> dual { return sin(a); };
    CHECK(std::fabs(val(f3(z)) - std::sin(1.0)) < 1e-10);
    CHECK(std::fabs(derivative(f3, wrt(z), z) - std::cos(1.0)) < 1e-10);
    std::cout << "PASS: forward mode — sin derivative OK" << std::endl;

    // Test 5: exp(x) derivative
    auto f4 = [](dual a) -> dual { return exp(a); };
    CHECK(std::fabs(val(f4(z)) - std::exp(1.0)) < 1e-10);
    CHECK(std::fabs(derivative(f4, wrt(z), z) - std::exp(1.0)) < 1e-10);
    std::cout << "PASS: forward mode — exp derivative OK" << std::endl;

    // Test 6: binary function gradient f(x,y)=x*y
    x = 3.0;
    y = 4.0;
    auto f5 = [](dual a, dual b) -> dual { return a * b; };
    CHECK(std::fabs(val(f5(x, y)) - 12.0) < 1e-10);
    CHECK(std::fabs(derivative(f5, wrt(x), x, y) - 4.0) < 1e-10);
    CHECK(std::fabs(derivative(f5, wrt(y), x, y) - 3.0) < 1e-10);
    std::cout << "PASS: forward mode — binary gradient OK" << std::endl;

    std::cout << std::endl << "All autodiff forward-mode consumer tests PASSED." << std::endl;
    return 0;
}
