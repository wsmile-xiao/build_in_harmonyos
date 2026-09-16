cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(libff REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE libff::ff)
target_compile_features(test_package PRIVATE cxx_std_11)

# HarmonyOS 专项消费者测试（对标 archives/a/au、archives/b/boost 先例）:
# 针对本次适配的真实平台差异点（NO_PROCPS 回退、aarch64 可移植 Montgomery
# 路径、跨架构常数一致性、配对确定性、zero 序列化分支），非上游测试复述。
add_executable(test_package_ohos test_package_ohos.cpp)
target_link_libraries(test_package_ohos PRIVATE libff::ff)
target_compile_features(test_package_ohos PRIVATE cxx_std_11)
# 鸿蒙专项的对象级检查需要定位**包内**（而非构建树）的 libff.a：CMakeDeps
# 的 libff::ff 是 INTERFACE IMPORTED 包装目标（无 IMPORTED_LOCATION，
# $<TARGET_FILE> 不可用），故由 test_package 配方在 configure 时以
# -DLIBFF_ARCHIVE_PATH=<conan 包内归档绝对路径> 注入，测试解析 ar/ELF 头。
if(NOT DEFINED LIBFF_ARCHIVE_PATH)
    message(FATAL_ERROR "LIBFF_ARCHIVE_PATH must be passed by the test_package conanfile")
endif()
target_compile_definitions(test_package_ohos PRIVATE
    LIBFF_ARCHIVE_PATH="${LIBFF_ARCHIVE_PATH}")

enable_testing()
add_test(NAME test_package COMMAND test_package)
add_test(NAME test_package_ohos COMMAND test_package_ohos)
