cmake_minimum_required(VERSION 3.15)
project(test_folly CXX)

find_package(folly CONFIG REQUIRED)
find_package(gtest CONFIG REQUIRED)

add_executable(test_folly test_folly.cpp)
target_link_libraries(test_folly PRIVATE Folly::folly)
target_compile_features(test_folly PRIVATE cxx_std_20)

# rule4 真实执行上游 folly GTest 用例（OHOS 可构建/链接/运行）：
# 从上游 folly v2026.07.27.00 源码原样取回的 5 个纯单元测试文件，以真实
# 消费者身份链接安装后的 Folly::folly + gtest，编译期+链接期+运行期
# 全贯通，逐条统计 gtest 执行数与通过率。源文件不做任何修改（原样上游代码）。
# 上游测试体本身不含 main，统一由 gtest_main.cpp 提供 gtest 入口
# （InitGoogleTest + RUN_ALL_TESTS），编译为静态库后链入每个 upstream_<Name>。
add_library(gtest_main STATIC gtest_main.cpp)
# gtest_main.cpp 编译期即 need gtest 头/宏，故自身链接 gtest::gtest。
target_link_libraries(gtest_main PRIVATE gtest::gtest)

set(UPSTREAM_TESTS
    ConvTest
    FBStringTest
    FixedStringTest
    BitsTest
    RandomTest
)
foreach(t IN LISTS UPSTREAM_TESTS)
    add_executable(upstream_${t} upstream_tests/${t}.cpp)
    target_link_libraries(upstream_${t} PRIVATE
        Folly::folly
        gtest::gtest
        gtest_main
    )
    target_compile_features(upstream_${t} PRIVATE cxx_std_20)
endforeach()

enable_testing()
add_test(NAME folly_test COMMAND test_folly)
foreach(t IN LISTS UPSTREAM_TESTS)
    add_test(NAME upstream_${t} COMMAND upstream_${t})
endforeach()
