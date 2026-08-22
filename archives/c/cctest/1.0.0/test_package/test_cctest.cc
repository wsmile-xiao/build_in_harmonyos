#include "cctest/cctest.h"

using namespace cctest;

namespace {

FIXTURE(SmokeTest) {
  TEST("two plus two equals four") {
    ASSERT_EQ(2 + 2, 4);
  }

  TEST("true is true") {
    ASSERT_TRUE(true);
  }
};

}

int main(int argc, char* argv[]) {
  return cctest::run_all_tests(argc, argv);
}