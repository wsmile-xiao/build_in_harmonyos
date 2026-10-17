cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(cpptrace REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE cpptrace::cpptrace)
target_compile_features(test_package PRIVATE cxx_std_11)

# OHOS musl does not emit unwind tables at -O2 by default; required for
# the stack walker to see frames from this translation unit.
if(NOT MSVC)
    target_compile_options(test_package PRIVATE -funwind-tables)
endif()

enable_testing()
add_test(NAME test_package COMMAND test_package)

add_executable(test_cpptrace_ohos test_ohos.cpp)
target_link_libraries(test_cpptrace_ohos PRIVATE cpptrace::cpptrace)
target_compile_features(test_cpptrace_ohos PRIVATE cxx_std_11)
if(NOT MSVC)
    target_compile_options(test_cpptrace_ohos PRIVATE -funwind-tables)
endif()
add_test(NAME test_cpptrace_ohos COMMAND test_cpptrace_ohos)
