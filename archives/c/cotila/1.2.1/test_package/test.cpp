#include <cotila/cotila.h>

#include <cassert>
#include <iostream>

// cotila 1.2.1 — header-only compile-time linear algebra (consumer
// verification).  Verifies that the headers compile with OHOS clang/libc++
// (C++17), that constexpr evaluation works at compile time (static_assert
// is checked by the compiler itself), and that the runtime path computes
// the same results.
int main() {
    // 1) Compile-time: dot product of (1,2,3) with itself is 14.
    constexpr auto v = cotila::make_vector(1.0, 2.0, 3.0);
    static_assert(cotila::dot(v, v) == 14.0, "constexpr dot product failed");

    // 2) Compile-time: trace of the 2x2 identity-scaled matrix is 5.
    constexpr cotila::matrix<double, 2, 2> m{{{1.0, 2.0}, {3.0, 4.0}}};
    static_assert(cotila::trace(m) == 5.0, "constexpr trace failed");

    // 3) Runtime: same results computed and printed.
    const double d = cotila::dot(v, v);
    const double t = cotila::trace(m);
    std::cout << "cotila ok: dot=" << d << " trace=" << t << std::endl;
    assert(d == 14.0);
    assert(t == 5.0);
    return 0;
}
