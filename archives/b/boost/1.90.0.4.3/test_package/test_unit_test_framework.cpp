// Boost.Test dynamic-link consumer for boost/1.90.0.4.2.
// Mirrors the pinocchio 4.1.0 upstream unittest pattern:
//   find_package(Boost COMPONENTS unit_test_framework)
//   target_link_libraries(... Boost::unit_test_framework)
//   target_compile_definitions(... BOOST_TEST_DYN_LINK)
#define BOOST_TEST_MODULE boost_unit_test_framework_consumer
#include <boost/test/unit_test.hpp>

BOOST_AUTO_TEST_CASE(boost_test_smoke) {
    BOOST_TEST(1 + 1 == 2);
    BOOST_TEST(true);
}
