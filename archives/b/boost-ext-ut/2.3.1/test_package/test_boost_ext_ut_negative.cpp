// test_boost_ext_ut_negative.cpp — negative probe for boost-ext-ut 2.3.1
// One deliberately failing expectation: the default runner MUST report the
// failure and exit non-zero. The Conan test() step inverts the exit code, so
// a runner that silently returned 0 would fail the package test.
#include <boost/ut.hpp>

int main() {
  using namespace boost::ut;

  "passes"_test = [] { expect(1_i == 1); };
  "deliberately fails"_test = [] { expect(1_i == 2) << "this expectation is meant to fail"; };

  return 0;
}
