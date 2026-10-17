// Consumer test for libclaw 1.7.4: links the installed libraries and calls
// real public APIs. 6 explicit checks; any failure returns non-zero.
#include <claw/tween/single_tweener.hpp>
#include <claw/tween/easing/easing_linear.hpp>
#include <claw/box_2d.hpp>
#include <claw/configuration_file.hpp>

#include <cmath>
#include <iostream>
#include <sstream>

#define CHECK(cond) \
    do { \
        if (!(cond)) { \
            std::cerr << "CHECK failed line " << __LINE__ << ": " #cond << std::endl; \
            return 1; \
        } \
    } while (0)

int main() {
    // 1-2: tween single_tweener runs to finish and reaches the end value.
    double last = 0.0;
    claw::tween::single_tweener t(
        0.0, 10.0, 1.0,
        [&last](double v) { last = v; },
        &claw::tween::easing_linear::ease_in);
    t.update(0.0);
    while (!t.is_finished()) {
        t.update(0.1);
    }
    CHECK(t.is_finished());                    // check 1
    CHECK(std::fabs(last - 10.0) < 1e-6);      // check 2

    // 3-4: box_2d geometry over integers.
    claw::math::box_2d<int> b(0, 0, 4, 3);
    CHECK(b.width() == 4);                     // check 3
    CHECK(b.area() == 12);                     // check 4

    // 5-6: configuration_file parses an ini section from a stream.
    std::istringstream is("[video]\nwidth = 800\n");
    claw::configuration_file::syntax_description syntax;
    claw::configuration_file conf(is, syntax);
    CHECK(conf.has_field("video", "width"));   // check 5
    CHECK(conf("video", "width") == "800");    // check 6

    std::cout << "libclaw consumer test: 6/6 checks passed" << std::endl;
    return 0;
}
