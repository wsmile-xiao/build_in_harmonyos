// test_package/test_ohos.cpp - libtut 0.0.20070706 HarmonyOS-specific test
//
// Exercises OHOS platform characteristics THROUGH the framework:
//   - a TUT test group, compiled only on the OHOS toolchain (#ifdef __OHOS__),
//     asserting: toolchain macro contract, musl sysconf behavior, and the
//     HarmonyOS kernel utsname (sysname "HarmonyOS", machine matching the
//     compile-time __aarch64__ arch)
//   - main() additionally drives tut_restartable.hpp (the third packaged
//     header, otherwise uncovered): its journal.tut/log.tut ofstream/
//     ifstream persistence + replay path on the OHOS filesystem
//
// On non-OHOS hosts (e.g. local MSVC verification) the group is compiled
// out and the driver asserts that exactly 0 groups are registered - the
// compile gate is itself part of the contract under test.
//
// ASCII-only comments on purpose: MSVC reads sources as CP936 by default.

#include <tut/tut.hpp>
#include <tut/tut_restartable.hpp>

#include <cstdio>
#include <map>
#include <string>

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
    void run_started() { per_group.clear(); }

    void test_completed(const tut::test_result& tr)
    {
        counters& c = per_group[tr.group];
        ++c.total;
        switch (tr.result)
        {
        case tut::test_result::ok:   ++c.ok;   break;
        case tut::test_result::fail: ++c.fail; break;
        case tut::test_result::ex:   ++c.ex;   break;
        default: break;
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

#ifdef __OHOS__

#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>

namespace tut
{

struct ohos_data
{
};

typedef test_group<ohos_data> ohos_tf;
typedef ohos_tf::object object;
namespace { ohos_tf ohos_group("ohos platform characteristics"); }

template<> template<>
void object::test<1>()
{
    set_test_name("OHOS toolchain macro and arch consistency");
    // this TU only registers the group when __OHOS__ is predefined by the
    // OHOS clang; reaching this test already proves the compile gate
    const bool ohos_toolchain =
#ifdef __OHOS__
        true;
#else
        false;
#endif
    ensure("__OHOS__ predefined by OHOS toolchain", ohos_toolchain);

    const char* compile_arch =
#ifdef __aarch64__
        "aarch64";
#else
        "unknown";
#endif
    struct utsname u;
    ensure_equals("uname() succeeds on musl/OHOS", uname(&u), 0);
    ensure_equals("runtime machine matches compile-time arch",
                  std::string(u.machine), std::string(compile_arch));
}

template<> template<>
void object::test<2>()
{
    set_test_name("musl sysconf: processors and page size");
    const long ncpu = sysconf(_SC_NPROCESSORS_CONF);
    ensure("cpu count configured", ncpu >= 1);
    const long page = sysconf(_SC_PAGESIZE);
    ensure("page size positive", page > 0);
}

template<> template<>
void object::test<3>()
{
    set_test_name("HarmonyOS kernel utsname");
    struct utsname u;
    ensure_equals("uname() succeeds", uname(&u), 0);
    ensure_equals("sysname is HarmonyOS (HM kernel)",
                  std::string(u.sysname), std::string("HarmonyOS"));
    ensure("release string non-empty", std::string(u.release).size() > 0);
}

} // namespace tut

#endif // __OHOS__

int main()
{
    // phase A: normal runner pass with exact accounting
    counting_callback cnt;
    tut::runner.get().set_callback(&cnt);
    tut::runner.get().run_tests();

#ifdef __OHOS__
    check(cnt.per_group.size() == 1,
          "ohos platform group registered on OHOS toolchain");
    std::map<std::string, counters>::const_iterator g =
        cnt.per_group.find("ohos platform characteristics");
    check(g != cnt.per_group.end(), "ohos group ran");
    if (g != cnt.per_group.end())
    {
        check(g->second.total == 3, "ohos group: 3 tests run");
        check(g->second.ok == 3 && g->second.fail == 0 && g->second.ex == 0,
              "ohos group: 3 ok / 0 fail / 0 ex");
    }

    // phase B: tut_restartable.hpp journal persistence + replay on OHOS fs
    const std::string jdir = "ohos-journal-probe";
    ::mkdir(jdir.c_str(), 0755);  // EEXIST from a previous run is fine

    // NB: restartable_wrapper's invoke_callback_() REPLACES the runner's
    // callback with the wrapper's one and never restores it, so callback
    // objects must outlive every wrapper run - both are declared at main()
    // scope on purpose (a per-block callback dangles once its block ends
    // and the next wrapper run segfaults inside callback_->run_started()).
    counting_callback rcb_run1;
    counting_callback rcb_run2;

    {
        tut::restartable_wrapper rw(jdir);
        rw.set_callback(&rcb_run1);
        rw.run_tests();  // executes + replays journal via callback

        std::map<std::string, counters>::const_iterator jg =
            rcb_run1.per_group.find("ohos platform characteristics");
        check(jg != rcb_run1.per_group.end() && jg->second.total == 3 &&
              jg->second.ok == 3,
              "restartable run 1: journal replay delivers 3/3 ok");

        struct stat st;
        check(::stat((jdir + "/journal.tut").c_str(), &st) == 0,
              "journal.tut exists after run (truncate-on-success marker)");
        check(::stat((jdir + "/log.tut").c_str(), &st) == 0,
              "log.tut exists after run");
    }
    {
        // second wrapper run over the truncated state: full re-execution
        // and replay must be idempotent on the OHOS filesystem
        tut::restartable_wrapper rw(jdir);
        rw.set_callback(&rcb_run2);
        rw.run_tests();
        std::map<std::string, counters>::const_iterator jg =
            rcb_run2.per_group.find("ohos platform characteristics");
        check(jg != rcb_run2.per_group.end() && jg->second.total == 3 &&
              jg->second.ok == 3,
              "restartable run 2 (after truncate): 3/3 ok again");
    }
    std::printf("note: ohos-journal-probe/ left in cwd (journal/log)\n");
#else
    check(cnt.per_group.empty(),
          "non-OHOS host: ohos group correctly compiled out (0 groups)");
    std::printf("SKIP: OHOS-specific phases compiled out on this host\n");
#endif

    if (g_failures == 0)
    {
        std::printf("test_ohos: ALL CHECKS PASSED\n");
    }
    return g_failures == 0 ? 0 : 1;
}
