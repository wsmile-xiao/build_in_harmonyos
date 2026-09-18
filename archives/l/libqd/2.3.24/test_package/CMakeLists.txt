cmake_minimum_required(VERSION 3.15)
project(test_libqd LANGUAGES CXX)

find_package(libqd REQUIRED)

add_executable(test_libqd test.cpp)
target_compile_features(test_libqd PRIVATE cxx_std_17)
target_link_libraries(test_libqd PRIVATE libqd::libqd)

enable_testing()
add_test(NAME test_libqd COMMAND test_libqd)
