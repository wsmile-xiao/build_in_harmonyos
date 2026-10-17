#ifndef __OHOS__
#error "HarmonyOS-specific test must be compiled by the OHOS toolchain"
#endif

#ifndef BOOST_STACKTRACE_USE_NOOP
#error "The package target must propagate BOOST_STACKTRACE_USE_NOOP"
#endif

#include <boost/config.hpp>
#include <boost/stacktrace.hpp>
#include <boost/stacktrace/safe_dump_to.hpp>

#include <array>
#include <cerrno>
#include <cstddef>
#include <cstdio>
#include <iostream>

namespace {

bool check(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        return false;
    }
    return true;
}

BOOST_NOINLINE boost::stacktrace::stacktrace capture_level_three() {
    return boost::stacktrace::stacktrace();
}

BOOST_NOINLINE boost::stacktrace::stacktrace capture_level_two() {
    return capture_level_three();
}

BOOST_NOINLINE boost::stacktrace::stacktrace capture_level_one() {
    return capture_level_two();
}

}  // namespace

int main() {
    bool ok = true;

    const boost::stacktrace::stacktrace trace = capture_level_one();
    ok &= check(trace.empty(),
                "nested HarmonyOS noop capture must remain empty");
    ok &= check(trace.size() == 0,
                "nested HarmonyOS noop capture size must be zero");

    std::array<unsigned char, 512> storage{};
    storage.fill(0xA5);
    ok &= check(boost::stacktrace::safe_dump_to(
                    0, storage.data(), storage.size()) == 1,
                "HarmonyOS noop memory dump must contain only its terminator");
    bool zero_terminator = true;
    for (std::size_t index = 0; index < sizeof(void*); ++index) {
        zero_terminator &= storage[index] == 0;
    }
    ok &= check(zero_terminator,
                "HarmonyOS noop memory dump must write a zero terminator");

    const char* dump_file = "boost_stacktrace_noop_ohos.dump";
    std::remove(dump_file);
    ok &= check(boost::stacktrace::safe_dump_to(dump_file) == 0,
                "HarmonyOS noop file dump must contain zero frames");

    errno = 0;
    std::FILE* file = std::fopen(dump_file, "rb");
    if (file != nullptr) {
        ok &= check(std::fgetc(file) == EOF,
                    "HarmonyOS noop file dump must not contain frame data");
        std::fclose(file);
        std::remove(dump_file);
    } else {
        ok &= check(errno == ENOENT,
                    "HarmonyOS noop file dump may only omit an empty file");
    }

    if (ok) {
        std::cout << "HarmonyOS boost stacktrace noop test passed\n";
    }
    return ok ? 0 : 1;
}
