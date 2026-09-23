#include <boost/stacktrace.hpp>
#include <boost/stacktrace/safe_dump_to.hpp>

#include <array>
#include <cstddef>
#include <iostream>
#include <sstream>

namespace {

bool check(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        return false;
    }
    return true;
}

}  // namespace

int main() {
    bool ok = true;

    const boost::stacktrace::stacktrace trace;
    ok &= check(trace.empty(), "noop stacktrace must be empty");
    ok &= check(trace.size() == 0, "noop stacktrace size must be zero");
    ok &= check(trace.begin() == trace.end(),
                "noop stacktrace iterator range must be empty");

    const boost::stacktrace::stacktrace copied(trace);
    ok &= check(copied == trace, "copied noop stacktrace must compare equal");

    std::ostringstream formatted;
    formatted << trace;
    ok &= check(formatted.str().empty(),
                "formatted noop stacktrace must be empty");

    std::array<unsigned char, 256> storage{};
    storage.fill(0xA5);
    const std::size_t dumped = boost::stacktrace::safe_dump_to(
        0, storage.data(), storage.size());
    ok &= check(dumped == 1,
                "noop memory dump must contain only its zero terminator");
    bool zero_terminator = true;
    for (std::size_t index = 0; index < sizeof(void*); ++index) {
        zero_terminator &= storage[index] == 0;
    }
    ok &= check(zero_terminator,
                "noop memory dump must write a zero pointer terminator");

    if (ok) {
        std::cout << "boost stacktrace noop consumer test passed\n";
    }
    return ok ? 0 : 1;
}
