cmake_minimum_required(VERSION 3.15)
project(test_boost1_84_stacktrace_basic CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(boost1.84-stacktrace_basic REQUIRED CONFIG COMPONENTS stacktrace_basic)

add_executable(test_boost1_84_stacktrace_basic test_boost_stacktrace_basic.cpp)
target_link_libraries(test_boost1_84_stacktrace_basic PRIVATE boost1.84-stacktrace_basic::stacktrace_basic)

# basic 实现的 frame::name() 依赖 dladdr 解析动态符号表；-rdynamic 把
# 可执行文件自身的符号导出进动态表（上游测试同款 FORCE_SYMBOL_EXPORT）。
target_link_options(test_boost1_84_stacktrace_basic PRIVATE -rdynamic)

# OHOS：测试二进制静态链接 libc++ 运行时（-static-libstdc++），
# 运行时不依赖 LD_LIBRARY_PATH 指向 SDK 的 libc++_shared.so——
# conanrun 环境不含 profile buildenv 的 SDK 库路径，动态链接会导致
# "Error loading shared library libc++_shared.so" (rc=127)。
target_link_options(test_boost1_84_stacktrace_basic PRIVATE -static-libstdc++)

enable_testing()
add_test(NAME boost1_84_stacktrace_basic_test COMMAND test_boost1_84_stacktrace_basic)
