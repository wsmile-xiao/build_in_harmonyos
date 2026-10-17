// Replaces upstream tests/main.cpp (which only defined BOOST_TEST_MODULE and
// relied on the compiled Boost.Test runner to provide main()).
#include <boost/test/unit_test.hpp>

int main() { return ::shim_boost_test::run_all(); }
