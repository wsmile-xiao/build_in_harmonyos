// test_tl.cpp — tl (tl-expected) 1.3.1 real consumer test.
// Uses the installed Conan package header include/tl/expected.hpp via tl::expected.
// Covers both "has value" and "error value" semantics with real assertions.
#include <cstdio>
#include <string>

#include <tl/expected.hpp>

static int failures = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        if (!(cond)) {                                                       \
            std::fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__);   \
            ++failures;                                                      \
        }                                                                    \
    } while (0)

int main() {
    // ---- has-value semantics ----
    tl::expected<int, std::string> ok{42};
    CHECK(ok.has_value());
    CHECK(static_cast<bool>(ok));
    CHECK(ok.value() == 42);
    CHECK(*ok == 42);
    CHECK(ok.value_or(0) == 42);

    // ---- error-value semantics ----
    tl::expected<int, std::string> err{tl::unexpect, "boom"};
    CHECK(!err.has_value());
    CHECK(!static_cast<bool>(err));
    CHECK(err.error() == "boom");
    CHECK(err.value_or(7) == 7);

    // unexpected + make_unexpected
    auto u = tl::make_unexpected(std::string{"oops"});
    tl::expected<int, std::string> err2{u};
    CHECK(!err2.has_value());
    CHECK(err2.error() == "oops");

    // value() on error must throw bad_expected_access (exceptions enabled upstream)
    bool threw = false;
    try {
        (void)err.value();
    } catch (const tl::bad_expected_access<std::string>&) {
        threw = true;
    }
    CHECK(threw);

    // map / and_then functional extensions
    auto mapped = ok.map([](int v) { return v * 2; });
    CHECK(mapped.has_value());
    CHECK(mapped.value() == 84);
    auto flat = err.and_then([](int) -> tl::expected<int, std::string> { return 1; });
    CHECK(!flat.has_value());
    CHECK(flat.error() == "boom");

    if (failures != 0) {
        std::fprintf(stderr, "test_tl: %d assertion(s) failed\n", failures);
        return 1;
    }
    std::printf("test_tl: all assertions passed\n");
    return 0;
}
