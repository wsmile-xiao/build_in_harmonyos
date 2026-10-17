// test_lexy_ohos.cpp — lexy 2025.05.0 HarmonyOS-specific test
//
// Objective 1 (R04): a Harmony-specific test that actually exercises lexy's
// API on the OHOS (aarch64, musl) native toolchain and validates OHOS
// platform behavior — not a string-only stub, not compile-only, and not a
// duplicate of the upstream CTest suite.
//
// What it verifies:
//   1. Build-time platform macros: __OHOS__ and __aarch64__ must be defined
//      (this file is compiled with the OHOS native clang, so both are set).
//   2. lexy::parse actually parses a signed integer DSL grammar.
//   3. lexy::read_file() reads a real file from the OHOS filesystem and the
//      parsed value matches the file contents (exercises the compiled
//      lexy_file component: src/input/file.cpp on the OHOS file I/O path).
//
// The file to read is created under the current worktree (a writable OHOS
// filesystem location) before running, then passed as argv[1].

#include <lexy/action/parse.hpp>
#include <lexy/callback.hpp>
#include <lexy/dsl.hpp>
#include <lexy/input/file.hpp>
#include <lexy/input/string_input.hpp>

#include <cstdio>
#include <cstdlib>
#include <string>

namespace dsl = lexy::dsl;

// Signed integer grammar (same shape as upstream examples/json.cpp exponent).
struct integer {
    static constexpr auto rule  = dsl::sign + dsl::integer<int>;
    static constexpr auto value = lexy::as_integer<int>;
};

static int failures = 0;

#define CHECK(cond, msg)                                                \
    do {                                                                \
        if (!(cond)) {                                                  \
            std::fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__); \
            ++failures;                                                 \
        }                                                               \
    } while (0)

int main(int argc, char** argv) {
    // ── 1) OHOS platform macros ──
#ifdef __OHOS__
    std::printf("platform: __OHOS__ defined\n");
#else
    std::printf("FAIL: __OHOS__ not defined\n");
    ++failures;
#endif
#ifdef __aarch64__
    std::printf("platform: __aarch64__ defined\n");
#else
    std::printf("FAIL: __aarch64__ not defined\n");
    ++failures;
#endif

    // ── 2) lexy::parse in-memory integer parsing ──
    {
        auto r = lexy::parse<integer>(lexy::zstring_input("42"), lexy::noop);
        CHECK(r.has_value(), "parse \"42\" has value");
        if (r.has_value())
            CHECK(r.value() == 42, "parse \"42\" == 42");
    }
    {
        auto r = lexy::parse<integer>(lexy::zstring_input("-17"), lexy::noop);
        CHECK(r.has_value(), "parse \"-17\" has value");
        if (r.has_value())
            CHECK(r.value() == -17, "parse \"-17\" == -17");
    }

    // ── 3) lexy::read_file on the OHOS filesystem ──
    if (argc < 2) {
        std::fprintf(stderr, "FAIL: missing file path argument\n");
        ++failures;
    } else {
        auto file = lexy::read_file<lexy::utf8_encoding>(argv[1]);
        CHECK(static_cast<bool>(file), "read_file succeeds");
        if (file) {
            // Parse the integer from the file contents.
            auto input = lexy::string_input(file.buffer().data(),
                                            file.buffer().size());
            auto r     = lexy::parse<integer>(input, lexy::noop);
            CHECK(r.has_value(), "parse file contents has value");
            if (r.has_value())
                CHECK(r.value() == 42, "parse file contents == 42");
        }
    }

    if (failures == 0) {
        std::printf("PASS: lexy OHOS test (platform macros + parse + read_file)\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL: %d assertion(s) failed\n", failures);
    return 1;
}
