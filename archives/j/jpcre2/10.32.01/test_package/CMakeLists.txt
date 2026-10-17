cmake_minimum_required(VERSION 3.15)
project(test_jpcre2 CXX)

find_package(jpcre2 REQUIRED)
find_package(pcre2 REQUIRED)

add_executable(test_jpcre2 test_jpcre2.cpp)
target_link_libraries(test_jpcre2 jpcre2::jpcre2)
target_compile_features(test_jpcre2 PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_jpcre2 COMMAND test_jpcre2)
