// test_consumer.cpp — libhpptools 1.1.1 test_package
// HarmonyOS PC adaptation: consumer-perspective smoke test.
//
// The upstream Catch suite (test_alg.cpp) only exercises alg.hpp. This
// binary covers the remaining packaged headers with real API calls and
// assertions on OHOS aarch64:
//   zstr (gzip roundtrip incl. multi-member), tpool, pfor, logger,
//   logsum, logsumset, logdiff, strict_fstream.
//
// Upstream test coverage note (test-zstr.make drives zc/zpipe/ztxtpipe via
// shell pipelines; those are CLI examples, not library headers — the core
// zstr stream behavior is re-validated here in-process).
#include <atomic>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <iostream>
#include <iterator>
#include <sstream>
#include <string>
#include <vector>

#include "logdiff.hpp"
#include "logger.hpp"
#include "logsum.hpp"
#include "logsumset.hpp"
#include "pfor.hpp"
#include "strict_fstream.hpp"
#include "tpool.hpp"
#include "zstr.hpp"

static int g_failures = 0;
static int g_checks = 0;

#define CHECK_MSG(cond, msg)                                                   \
    do                                                                         \
    {                                                                          \
        ++g_checks;                                                            \
        if (!(cond))                                                           \
        {                                                                      \
            ++g_failures;                                                      \
            std::cout << "FAIL: " << msg << " (line " << __LINE__ << ")\n";    \
        }                                                                      \
    } while (0)

static void test_zstr()
{
    // 1) in-memory gzip roundtrip through the zstr stream wrappers.
    const std::string payload = "hello zlib via hpptools zstr wrapper";
    std::stringstream compressed;
    {
        zstr::ostream zo(compressed);
        zo << payload;
    }
    CHECK_MSG(compressed.str().size() > 0, "zstr::ostream produced no output");
    CHECK_MSG(compressed.str() != payload, "zstr::ostream output is not compressed");

    std::stringstream compressed_in(compressed.str());
    zstr::istream zi(compressed_in);
    std::string roundtrip((std::istreambuf_iterator< char >(zi)),
                          std::istreambuf_iterator< char >());
    CHECK_MSG(roundtrip == payload, "zstr gzip roundtrip mismatch");

    // 2) multi-member stream: two concatenated gzip members (mirrors the
    //    upstream test-zstr.make `{ gzip; gzip; } | ztxtpipe` cases).
    std::string member = payload + "\n";
    std::string two_members;
    for (int m = 0; m < 2; ++m)
    {
        std::stringstream cs;
        {
            zstr::ostream zo(cs);
            zo << member;
        }
        two_members += cs.str();
    }
    std::stringstream multi_in(two_members);
    zstr::istream zi2(multi_in);
    std::string joined((std::istreambuf_iterator< char >(zi2)),
                       std::istreambuf_iterator< char >());
    CHECK_MSG(joined == member + member, "zstr multi-member gzip roundtrip mismatch");
}

static void test_strict_fstream()
{
    const std::string fname = "hpptools_sfs_test.tmp";
    const std::string text = "strict_fstream line\n";
    {
        strict_fstream::ofstream out(fname);
        out << text;
    }
    {
        strict_fstream::ifstream in(fname);
        std::string got;
        std::getline(in, got);
        CHECK_MSG(got + "\n" == text, "strict_fstream write/read mismatch");
    }
    std::remove(fname.c_str());
}

static void test_logger()
{
    logger::Logger::set_default_level(logger::info);
    int c = 0;
    LOG(info) << "now you see me; c=" << ++c << "\n";
    bool seen = (c == 1);
    LOG(debug1) << "now you don't; c=" << ++c << "\n";
    CHECK_MSG(seen && c == 1, "logger level filtering wrong");
    logger::Logger::set_facility_level("tst", logger::error);
    CHECK_MSG(logger::Logger::get_facility_level("tst") == logger::error,
              "logger facility level roundtrip wrong");
}

static void test_logsum()
{
    const float a = 0.5f, b = 0.3f;
    const float expected = std::log(std::exp(a) + std::exp(b));
    const float got = logsum::p7_FLogsum(a, b);
    // p7_FLogsum is a table-driven approximation (p7_LOGSUM_TBL=16000 entries,
    // 0.001 nats resolution): tolerance 1e-3 matches the upstream design.
    CHECK_MSG(std::fabs(got - expected) < 1e-3f, "p7_FLogsum value wrong");

    logsum::logsumset< float > sset(false);
    sset.add(a);
    sset.add(b);
    CHECK_MSG(std::fabs(sset.val() - expected) < 1e-3f, "logsumset accumulation wrong");
}

static void test_logdiff()
{
    // log(a - b) == p7_FLogsum(a, logdiff::LogDiff(a, b)) up to rounding.
    const float a = 2.0f, b = 1.0f;
    const float got = logdiff::LogDiff(a, b);
    const float expected = std::log(std::exp(a) - std::exp(b));
    CHECK_MSG(std::fabs(got - expected) < 1e-3f, "logdiff value wrong");
}

static void test_tpool()
{
    std::atomic< unsigned > counter(0);
    {
        tpool::tpool pool(4);
        for (unsigned i = 0; i < 100; ++i)
        {
            pool.add_job([&counter](unsigned) { ++counter; });
        }
        pool.wait_jobs();
    }
    CHECK_MSG(counter == 100, "tpool job count wrong");
}

static void test_pfor()
{
    std::vector< unsigned > v(1000, 0);
    std::atomic< unsigned > next(0);
    pfor::pfor< unsigned >(
        4, 10,
        [&](unsigned& i) -> bool
        {
            unsigned idx = next.fetch_add(1);
            if (idx >= v.size())
                return false;
            i = idx;
            return true;
        },
        [&](unsigned& i) { v[i] = i * i; });
    bool ok = true;
    for (unsigned i = 0; i < v.size(); ++i)
        ok = ok && (v[i] == i * i);
    CHECK_MSG(ok, "pfor results wrong");
}

int main()
{
    test_zstr();
    test_strict_fstream();
    test_logger();
    test_logsum();
    test_logdiff();
    test_tpool();
    test_pfor();

    std::cout << "test_consumer: " << (g_checks - g_failures) << "/" << g_checks
              << " checks passed" << std::endl;
    if (g_failures > 0)
    {
        std::cout << "test_consumer: FAIL" << std::endl;
        return 1;
    }
    std::cout << "test_consumer: PASS" << std::endl;
    return 0;
}
