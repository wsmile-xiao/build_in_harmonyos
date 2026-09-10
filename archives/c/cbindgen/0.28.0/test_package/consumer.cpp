#include "point.hpp"

#include <cmath>
#include <cstddef>
#include <cstdio>

static_assert(sizeof(CbindgenPoint) == 16, "Rust repr(C) size");
static_assert(offsetof(CbindgenPoint, y) == 8, "Rust repr(C) field offset");

int main() {
    CbindgenPoint point{5.0, 12.0};
    const double value = cbindgen_norm_sq(point);
    if (!std::isfinite(value) || std::fabs(value - 169.0) >= 0.000001)
        return 1;
    std::puts("CPP_FFI_RESULT=169");
    return 0;
}
