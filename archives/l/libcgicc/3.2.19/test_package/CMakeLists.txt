cmake_minimum_required(VERSION 3.15)
project(test_libcgicc CXX)

find_package(libcgicc REQUIRED)

add_executable(test_libcgicc test.cpp)
target_link_libraries(test_libcgicc libcgicc::libcgicc)

enable_testing()
add_test(NAME test_libcgicc COMMAND test_libcgicc)
