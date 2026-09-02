cmake_minimum_required(VERSION 3.16)
project(concurrencpp_harmonyos_test LANGUAGES CXX)

# HarmonyOS 专项测试（可复现构建入口）
# 用法: cmake -S . -B build -DCMAKE_PREFIX_PATH=<conan 包 prefix> && cmake --build build
find_package(concurrencpp REQUIRED)

add_executable(harmonyos_concurrency_test harmonyos_concurrency_test.cpp)
target_link_libraries(harmonyos_concurrency_test PRIVATE concurrencpp::concurrencpp)
target_compile_features(harmonyos_concurrency_test PRIVATE cxx_std_20)

enable_testing()
add_test(NAME harmonyos_concurrency_test COMMAND harmonyos_concurrency_test)