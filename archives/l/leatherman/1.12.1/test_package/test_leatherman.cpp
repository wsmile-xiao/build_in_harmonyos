// Consumer test for leatherman 1.12.1.
//
// Exercises six installed components through their real public APIs and
// prints HMBS_TEST_PACKAGE_RESULT with counters owned by this binary
// (no stdout scraping). Exit 0 only when every check passes.
//
// NOTE: <leatherman/locale/locale.hpp> and setup_logging() default to the
// PROJECT_NAME macro, which upstream consumer projects define via the
// leatherman CMake macros. Conan consumers define it themselves (below),
// exactly as facter/cpp-hocon do downstream.
#ifndef PROJECT_NAME
#define PROJECT_NAME "leatherman_test"
#endif

#ifndef LEATHERMAN_LOGGING_NAMESPACE
#define LEATHERMAN_LOGGING_NAMESPACE "leatherman.test"
#endif

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#include <leatherman/locale/locale.hpp>
#include <leatherman/util/uri.hpp>
#include <leatherman/util/environment.hpp>
#include <leatherman/json_container/json_container.hpp>
#include <leatherman/file_util/file.hpp>
#include <leatherman/logging/logging.hpp>

namespace lth_locale = leatherman::locale;
namespace lth_util = leatherman::util;
namespace lth_json = leatherman::json_container;
namespace lth_file = leatherman::file_util;
namespace lth_log = leatherman::logging;

static int checks_run = 0;
static int checks_failed = 0;

#define CHECK(cond) \
    do { \
        ++checks_run; \
        if (!(cond)) { \
            ++checks_failed; \
            std::cerr << "FAIL line " << __LINE__ << ": " #cond << std::endl; \
        } \
    } while (0)

static void check_locale() {
    // translate() with no installed catalog returns the input (upstream
    // locale/tests/format.cc expectation).
    CHECK(lth_locale::translate("requesting {1} item.") == "requesting {1} item.");
    // {N} placeholder substitution (boost::locale backend when locales
    // are enabled, boost::format fallback otherwise).
    CHECK(lth_locale::format("requesting {1} item.", 1) == "requesting 1 item.");
}

static void check_uri() {
    // Mirrors upstream util/tests/uri.cc "full uri" section (note: the
    // query keeps its leading '?').
    lth_util::uri u("https://foo:1234/bar?some=1&other=2");
    CHECK(u.protocol == "https");
    CHECK(u.host == "foo");
    CHECK(u.port == "1234");
    CHECK(u.path == "/bar");
    CHECK(u.query == "?some=1&other=2");
    CHECK(u.str() == "https://foo:1234/bar?some=1&other=2");
}

static void check_json() {
    lth_json::JsonContainer root("{\"name\": \"leatherman\", \"count\": 3}");
    CHECK(root.get<int>(lth_json::JsonContainerKey("count")) == 3);
    CHECK(root.type(lth_json::JsonContainerKey("name")) == lth_json::String);
    CHECK(root.includes(lth_json::JsonContainerKey("name")));
    CHECK(!root.includes(lth_json::JsonContainerKey("missing")));
}

static void check_file_util() {
    const char* tmpdir = std::getenv("TMPDIR");
    std::string path = std::string(tmpdir ? tmpdir : "/tmp")
        + "/leatherman_consumer_test.txt";
    {
        std::ofstream out(path.c_str());
        out << "harmony";
    }
    std::string contents;
    CHECK(lth_file::read(path, contents));
    CHECK(contents == "harmony");
    CHECK(lth_file::file_readable(path));
    std::remove(path.c_str());
}

static void check_environment() {
    CHECK(lth_util::environment::set("LEATHERMAN_CONSUMER_TEST_VAR", "42"));
    std::string value;
    CHECK(lth_util::environment::get("LEATHERMAN_CONSUMER_TEST_VAR", value)
        && value == "42");
}

static void check_logging() {
    // setup_logging() defaults to the warning level (upstream
    // logging/src/logging.cc), so LOG_WARNING must reach the sink.
    std::ostringstream sink;
    lth_log::setup_logging(sink);
    LOG_WARNING("consumer test message {1}", 42);
    CHECK(sink.str().find("consumer test message 42") != std::string::npos);
}

int main() {
    const int cases_total = 6;
    int cases_passed = 0;
    int before = 0;
#define RUN_CASE(fn) \
    do { \
        before = checks_failed; \
        fn(); \
        if (checks_failed == before) { \
            ++cases_passed; \
        } \
    } while (0)
    RUN_CASE(check_locale);
    RUN_CASE(check_uri);
    RUN_CASE(check_json);
    RUN_CASE(check_file_util);
    RUN_CASE(check_environment);
    RUN_CASE(check_logging);

    std::cout << "Results: " << cases_passed << "/" << cases_total
              << " consumer cases passed (" << (checks_run - checks_failed)
              << "/" << checks_run << " assertions)" << std::endl;
    std::cout << "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":"
              << (cases_passed == cases_total ? "true" : "false")
              << ",\"command\":\"./test_leatherman\",\"discovered\":"
              << cases_total
              << ",\"passedCount\":" << cases_passed
              << "}" << std::endl;
    return cases_passed == cases_total ? 0 : 1;
}
