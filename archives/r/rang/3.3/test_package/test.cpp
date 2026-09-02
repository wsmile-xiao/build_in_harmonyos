#include <rang.hpp>

#include <cassert>
#include <iostream>
#include <sstream>
#include <string>

// rang 3.3 — header-only terminal color/format library (consumer verification).
//
// Verifies that the rang.hpp header compiles, that the rang::fg / rang::bg /
// rang::style enums are usable, and that escape sequences are emitted when the
// control mode is left at the default (control::Auto on a color-enabled
// terminal). On HarmonyOS the header must compile cleanly with libc++ (C++11).
int main() {
    // 1) Style enumeration values exist and are distinct.
    assert(rang::fg::red != rang::fg::green);
    assert(rang::bg::blue != rang::bg::yellow);
    assert(rang::style::bold != rang::style::italic);
    assert(rang::style::reset == rang::style::reset);

    // 2) setControlMode / control mode plumbing compiles and runs.
    rang::setControlMode(rang::control::Off);
    rang::setWinTermMode(rang::winTerm::Auto);

    // 3) Streaming a fg color produces an ANSI SGR escape sequence when
    //    colors are enabled (default control mode on this run), i.e. the
    //    escape char '\033' is present in the formatted output.
    std::ostringstream os;
    rang::setControlMode(rang::control::Auto);
    os << rang::fg::red << "red" << rang::style::reset;
    std::string out = os.str();
    assert(out.find('\033') != std::string::npos);
    assert(out.find("red") != std::string::npos);

    // 4) With control::Off no escape sequences are emitted (plain text).
    rang::setControlMode(rang::control::Off);
    std::ostringstream os2;
    os2 << rang::fg::green << "green" << rang::style::reset;
    assert(os2.str() == "green");

    std::cout << "All rang consumer tests passed!" << std::endl;
    return 0;
}
