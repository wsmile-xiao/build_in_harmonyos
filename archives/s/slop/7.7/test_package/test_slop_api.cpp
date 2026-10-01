#include <cmath>
#include <cstdlib>
#include <cstring>
#include <iostream>

#include <slop.hpp>

namespace {

bool near(float actual, float expected) {
    return std::fabs(actual - expected) < 0.0001F;
}

}

int main() {
    unsetenv("DISPLAY");
    const slop_options options = slop_options_default();

    if (!near(options.border, 1.0F) ||
        !near(options.padding, 0.0F) ||
        !near(options.tolerance, 2.0F) ||
        !near(options.r, 0.5F) ||
        !near(options.g, 0.5F) ||
        !near(options.b, 0.5F) ||
        !near(options.a, 1.0F) ||
        options.xdisplay == nullptr ||
        std::strcmp(options.xdisplay, ":0") != 0) {
        std::cerr << "unexpected slop default options\n";
        return 1;
    }

    std::cout << "slop C API defaults: PASS\n";
    return 0;
}
