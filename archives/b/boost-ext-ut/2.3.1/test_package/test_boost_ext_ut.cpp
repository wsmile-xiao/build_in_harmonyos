// test_boost_ext_ut.cpp — consumer test for boost-ext-ut 2.3.1
// Writes a real boost.ut suite (the library under test IS the test framework):
// registers tests, evaluates expectations, exercises BDD/sections/parameterized
// and exception assertions. The default runner sets a non-zero exit code on any
// failed expectation, which the Conan test() step checks.
#include <boost/ut.hpp>

#include <stdexcept>
#include <string>
#include <vector>

int main() {
  using namespace boost::ut;

  // 1. basic expectations with integer literals / eq
  "arithmetic"_test = [] {
    expect(2_i == 1 + 1);
    expect(eq(6, 2 * 3));
    expect(that % 42 > 41);
  };

  // 2. string and container expectations
  "strings"_test = [] {
    const std::string s = "boost.ut";
    expect(s.size() == 8_u);
    expect(eq(s.substr(0, 5), std::string{"boost"}));
  };

  // 3. sections via should()
  "sections"_test = [] {
    std::vector<int> v{1, 2, 3};
    should("have size 3") = [&] { expect(v.size() == 3_u); };
    should("grow on push_back") = [&] {
      v.push_back(4);
      expect(v.size() == 4_u);
      expect(v.back() == 4_i);
    };
  };

  // 4. BDD given/when/then (DSL lives in boost::ut::bdd)
  "bdd"_test = [] {
    using namespace boost::ut::bdd;
    given("an empty vector") = [] {
      std::vector<int> v{};
      when("one element is pushed") = [&] {
        v.push_back(7);
        then("size becomes 1 and front is 7") = [&] {
          expect(v.size() == 1_u);
          expect(v.front() == 7_i);
        };
      };
    };
  };

  // 5. parameterized test over a value set
  "parameterized"_test = [](const auto& value) {
    expect(value > 0_i);
    expect(value % 2 == 1_i);
  } | std::vector{1, 3, 5, 7};

  // 6. exception assertions
  "exceptions"_test = [] {
    expect(throws<std::runtime_error>([] { throw std::runtime_error{"boom"}; }));
    expect(nothrow([] { return 1; }));
    expect(not throws([] {}));
  };

  return 0;  // default runner reports and adjusts the process exit code
}
