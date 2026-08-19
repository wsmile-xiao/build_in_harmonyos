// test_package/test.cpp — real Boost.Test consumer executable.
// Links the compiled Boost.Test static library (boost::unit_test_framework
// / Boost::unit_test_framework). The static library provides the main() entry
// (from unit_test_main.cpp); this translation unit supplies the user init
// function `init_unit_test` (alternative init API) and registers test cases.

#include <boost/test/unit_test.hpp>
#include <boost/test/unit_test_suite.hpp>
#include <boost/test/test_tools.hpp>

#include <string>

// User init function called by the Boost.Test library-provided main
// (compiled with BOOST_TEST_ALTERNATIVE_INIT_API).
bool init_unit_test()
{
    boost::unit_test::test_suite* probe_suite =
        BOOST_TEST_SUITE("probe_suite");

    probe_suite->add(BOOST_TEST_CASE(
        [] { BOOST_CHECK_EQUAL(1 + 1, 2); }));

    probe_suite->add(BOOST_TEST_CASE(
        [] {
            std::string a = "heart";
            std::string b = "beat";
            BOOST_REQUIRE_EQUAL(a + b, "heartbeat");
            BOOST_CHECK(a.size() == 5);
        }));

    probe_suite->add(BOOST_TEST_CASE(
        [] {
            // Ensure the compiled framework really runs a fresh test case.
            BOOST_TEST(true);
            BOOST_TEST(2 * 3 == 6);
        }));

    boost::unit_test::framework::master_test_suite().add(probe_suite);
    return true;
}
