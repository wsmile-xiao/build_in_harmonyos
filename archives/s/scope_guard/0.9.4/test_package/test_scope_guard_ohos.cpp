// scope_guard OHOS consumer test — L1 test_package (runs on HarmonyOS aarch64 host).
//
// HarmonyOS-specific focus: exercises the header-only C++11 RAII library
// end-to-end on the OHOS libc/clang toolchain. Covers SCOPE_EXIT macro,
// make_scope_exit/fail/success factories, dismiss(), move semantics,
// exception-path firing semantics, and the noexcept action types, which are
// the guarantees scope_guard must keep under the OHOS C++ ABI.
#include <cstdio>
#include <stdexcept>
#include <type_traits>
#include <utility>

#include <scope_guard.hpp>

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond, msg)                                            \
    do {                                                            \
        ++g_checks;                                                 \
        if (cond) {                                                 \
            std::printf("[PASS] %s\n", msg);                        \
        } else {                                                    \
            ++g_failures;                                           \
            std::printf("[FAIL] %s (line %d)\n", msg, __LINE__);    \
        }                                                           \
    } while (0)

namespace
{
    struct NoThrowAction
    {
        void operator()() & noexcept {}
    };
} // namespace

int main()
{
    int count = 0;

    // 1) SCOPE_EXIT macro: action runs on normal scope leave.
    {
        SCOPE_EXIT{ ++count; };
    }
    CHECK(count == 1, "SCOPE_EXIT runs cleanup on normal scope leave");

    // 2) make_scope_exit + dismiss(): dismissed guard must not run.
    {
        auto g = scope_guard::make_scope_exit([&count]() noexcept { ++count; });
        g.dismiss();
    }
    CHECK(count == 1, "dismissed scope_exit does not run");

    // 3) make_scope_fail: fires only when an exception escapes the scope.
    try
    {
        auto g = scope_guard::make_scope_fail([&count]() noexcept { ++count; });
        throw std::runtime_error{"boom"};
    }
    catch (std::runtime_error const&)
    {
    }
    CHECK(count == 2, "scope_fail fires when exception escapes");

    // 4) scope_fail must NOT fire on clean exit.
    {
        auto g = scope_guard::make_scope_fail([&count]() noexcept { ++count; });
    }
    CHECK(count == 2, "scope_fail does not fire on clean exit");

    // 5) make_scope_success: fires only on clean exit.
    {
        auto g = scope_guard::make_scope_success([&count]() noexcept { ++count; });
    }
    CHECK(count == 3, "scope_success fires on clean exit");

    // 6) scope_success must NOT fire when exception escapes.
    try
    {
        auto g = scope_guard::make_scope_success([&count]() noexcept { ++count; });
        throw std::runtime_error{"boom2"};
    }
    catch (std::runtime_error const&)
    {
    }
    CHECK(count == 3, "scope_success does not fire on exception");

    // 7) Guard is move-constructible, not copy-constructible (RAII ownership).
    using GuardT = decltype(scope_guard::make_scope_exit(NoThrowAction{}));
    CHECK(std::is_move_constructible<GuardT>::value,
          "scope_exit guard is move constructible");
    CHECK(!std::is_copy_constructible<GuardT>::value,
          "scope_exit guard is not copy constructible");
    static_assert(std::is_nothrow_destructible<GuardT>::value,
                  "scope_exit guard destructor must be noexcept");

    // 8) Move: transferred ownership runs exactly once.
    {
        auto g1 = scope_guard::make_scope_exit([&count]() noexcept { ++count; });
        auto g2 = std::move(g1);
        (void)g1;
    }
    CHECK(count == 4, "moved scope_exit runs cleanup exactly once");

    // 9) Multiple scope exits run in reverse order.
    {
        SCOPE_EXIT{ count = count * 10 + 1; };
        SCOPE_EXIT{ count = count * 10 + 2; };
    }
    CHECK(count == 421, "scope exits run in reverse order of declaration");

    // 10) Exception during execution does not corrupt subsequent guards.
    int fail_fired = 0;
    bool outer_ran = false;
    try
    {
        auto g = scope_guard::make_scope_fail([&fail_fired]() noexcept { ++fail_fired; });
        SCOPE_EXIT{ outer_ran = true; };
        throw std::runtime_error{"boom3"};
    }
    catch (std::runtime_error const&)
    {
    }
    CHECK(outer_ran, "nested SCOPE_EXIT still runs when exception escapes");
    CHECK(fail_fired == 1, "scope_fail fired alongside inner SCOPE_EXIT");

    std::printf("test_scope_guard_ohos: %d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}