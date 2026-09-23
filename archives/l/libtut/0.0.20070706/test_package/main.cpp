// test_package/main.cpp - libtut 0.0.20070706 consumer test
//
// Verifies the packaged headers work as a real consumer would use them:
//   - <tut/tut.hpp> (main header) + <tut/tut_reporter.hpp> are includable
//     and the official tut::reporter callback runs the full suite,
//     correctly reporting 1 intentional failure (all_ok() == false)
//   - a custom tut::callback subclass receives every test_result and
//     the exact per-group ok/fail/ex counts match what the two test
//     groups in group_core.cpp / group_shim.cpp deliberately produce
//   - cross-TU group registration (TUT's core architecture: each test
//     group lives in its own compilation unit and self-registers with
//     the tut::runner singleton defined here)
//
// Upstream ships its own suite (selftest/, ~84 test methods in 21 TUs)
// that is executed separately on the OHOS device; see notes.md.
//
// ASCII-only comments on purpose: MSVC reads sources as CP936 by default.

#include <tut/tut.hpp>
#include <tut/tut_reporter.hpp>

#include <cstdio>
#include <map>
#include <string>

// exactly one definition of the runner singleton per application
namespace tut
{
test_runner_singleton runner;
}

namespace
{

struct counters
{
    int total;
    int ok;
    int fail;
    int ex;
    counters() : total(0), ok(0), fail(0), ex(0) {}
};

class counting_callback : public tut::callback
{
public:
    void run_started()
    {
        per_group.clear();
    }

    void test_completed(const tut::test_result& tr)
    {
        counters& c = per_group[tr.group];
        ++c.total;
        switch (tr.result)
        {
        case tut::test_result::ok:
            ++c.ok;
            break;
        case tut::test_result::fail:
            ++c.fail;
            break;
        case tut::test_result::ex:
            ++c.ex;
            break;
        default:
            break;
        }
    }

    std::map<std::string, counters> per_group;
};

int g_failures = 0;

void check(bool cond, const char* what)
{
    if (cond)
    {
        std::printf("PASS: %s\n", what);
    }
    else
    {
        std::printf("FAIL: %s\n", what);
        ++g_failures;
    }
}

} // namespace

int main()
{
    // pass 1: official tut::reporter (exercises tut_reporter.hpp and
    // prints the standard TUT console output). group_core contains one
    // deliberately failing test, so all_ok() must be false.
    {
        tut::reporter reporter;
        tut::runner.get().set_callback(&reporter);
        tut::runner.get().run_tests();
        check(reporter.all_ok() == false,
              "tut::reporter runs suite and flags the 1 known failure");
    }

    // pass 2: counting callback for exact result-type assertions
    counting_callback cnt;
    tut::runner.get().set_callback(&cnt);
    tut::runner.get().run_tests();

    const std::map<std::string, counters>& g = cnt.per_group;

    check(g.size() == 2, "exactly 2 test groups registered across TUs");

    std::map<std::string, counters>::const_iterator core = g.find("core API");
    std::map<std::string, counters>::const_iterator shim =
        g.find("root shim include");

    check(core != g.end(), "group 'core API' (<tut/tut.hpp>) ran");
    if (core != g.end())
    {
        check(core->second.total == 4, "core group: 4 tests run");
        check(core->second.ok == 3, "core group: 3 ok");
        check(core->second.fail == 1, "core group: 1 expected failure");
        check(core->second.ex == 0, "core group: 0 unexpected exceptions");
    }

    check(shim != g.end(), "group 'root shim include' (<tut.h>) ran");
    if (shim != g.end())
    {
        check(shim->second.total == 2, "shim group: 2 tests run");
        check(shim->second.ok == 2 && shim->second.fail == 0,
              "shim group: 2 ok / 0 fail");
    }

    if (g_failures == 0)
    {
        std::printf("test_libtut: ALL CHECKS PASSED\n");
    }
    return g_failures == 0 ? 0 : 1;
}
