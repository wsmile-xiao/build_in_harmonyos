// gtest 统一入口：5 个上游 folly 测试体（ConvTest/FBStringTest/FixedStringTest/
// BitsTest/RandomTest）本身不含 main，统一由本文件提供
// InitGoogleTest + RUN_ALL_TESTS，链接进每个 upstream_<Name> 可执行文件。
#include <gtest/gtest.h>

int main(int argc, char** argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
