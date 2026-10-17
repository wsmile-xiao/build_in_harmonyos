// Trompeloeil consumer test — exercises the packaged header on OHOS aarch64.
#include <trompeloeil.hpp>

#include <catch2/catch_test_macros.hpp>

#include <string>

namespace {

struct mock_target
{
  MAKE_MOCK0(get_value, int());
  MAKE_MOCK1(set_name, void(const std::string&));
  MAKE_MOCK1(compute, int(int));
};

}  // namespace

TEST_CASE("mock call returns stubbed value", "[trompeloeil]")
{
  mock_target target;
  REQUIRE_CALL(target, get_value()).RETURN(42);
  CHECK(target.get_value() == 42);
}

TEST_CASE("argument matchers narrow the expectation", "[trompeloeil]")
{
  mock_target target;
  REQUIRE_CALL(target, compute(trompeloeil::gt(0))).TIMES(2).RETURN(7);
  CHECK(target.compute(3) == 7);
  CHECK(target.compute(100) == 7);
}

TEST_CASE("side effects observe call arguments", "[trompeloeil]")
{
  std::string observed;
  mock_target target;
  REQUIRE_CALL(target, set_name(trompeloeil::_)).LR_SIDE_EFFECT(observed = _1);
  target.set_name("harmonyos");
  CHECK(observed == "harmonyos");
}

TEST_CASE("unexpected calls raise expectation_violation", "[trompeloeil]")
{
  mock_target target;
  bool violation_reported = false;
  try {
    target.set_name("unexpected");  // no expectation -> fatal violation
  } catch (trompeloeil::expectation_violation const& e) {
    violation_reported = std::string(e.what()).find("unexpected") != std::string::npos;
  }
  CHECK(violation_reported);
}
