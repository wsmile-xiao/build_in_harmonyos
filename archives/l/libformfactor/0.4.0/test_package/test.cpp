#include "ff/Make.h"

#include <cmath>
#include <complex>
#include <memory>

int main()
{
    std::unique_ptr<ff::Box> box(ff::make::Box(2.0, 3.0, 4.0));
    if (!box) {
        return 1;
    }
    const C3 q{0.1, 0.2, 0.3};
    const auto value = box->formfactor(q);
    return std::isfinite(value.real()) && std::isfinite(value.imag()) ? 0 : 2;
}
