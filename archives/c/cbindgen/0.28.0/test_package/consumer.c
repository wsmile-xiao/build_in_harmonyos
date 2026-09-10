#include "point.h"

#include <math.h>
#include <stddef.h>
#include <stdio.h>

_Static_assert(sizeof(CbindgenPoint) == 16, "Rust repr(C) size");
_Static_assert(offsetof(CbindgenPoint, y) == 8, "Rust repr(C) field offset");

int main(void) {
    CbindgenPoint point = {3.0, 4.0};
    double value = cbindgen_norm_sq(point);
    if (!isfinite(value) || fabs(value - 25.0) >= 0.000001)
        return 1;
    puts("C_FFI_RESULT=25");
    return 0;
}
