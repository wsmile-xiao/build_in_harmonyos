#include <gmock/gmock.h>
#include <gtest/gtest.h>

#include <string>
#include <vector>


TEST(Arithmetic, AddsIntegers) { EXPECT_EQ(42, 19 + 23); }

TEST(StringMatchers, HasExpectedPrefix) {
  EXPECT_THAT(std::string("HarmonyOS"), testing::StartsWith("Harmony"));
}

TEST(ContainerMatchers, ElementsArePreserved) {
  const std::vector<int> values{1, 2, 3};
  EXPECT_THAT(values, testing::ElementsAre(1, 2, 3));
}
