# 消费者测试 — logfault 0.5.2（header-only 交付形态）
cmake_minimum_required(VERSION 3.15)
project(test_logfault CXX)

# 消费者视角：通过 Conan 生成的 CMakeDeps 找到 logfault 包
find_package(logfault REQUIRED CONFIG)

add_executable(test_logfault test_logfault.cpp)
target_link_libraries(test_logfault PRIVATE logfault::logfault)

# 上游测试位 CXX_STANDARD 14、头部自报 C++11 起；与 profile compiler.cppstd=17 同档
set_target_properties(test_logfault PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF)

enable_testing()
add_test(NAME logfault_consumer COMMAND test_logfault)
