cmake_minimum_required(VERSION 3.15)
project(test_googletest CXX)

# 与下游消费者（如 scnlib）完全一致的消费形态：上游 config 包名 GTest
find_package(GTest REQUIRED CONFIG)

add_executable(test_googletest test.cpp)
target_link_libraries(test_googletest PRIVATE GTest::gtest_main GTest::gmock)
set_property(TARGET test_googletest PROPERTY CXX_STANDARD 17)
