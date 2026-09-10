cmake_minimum_required(VERSION 3.15)
project(test_xapian_core CXX)

find_package(xapian REQUIRED)

add_executable(test_xapian_core test_xapian_core.cpp)
target_link_libraries(test_xapian_core xapian::xapian)

enable_testing()
add_test(NAME test_xapian_core COMMAND test_xapian_core)
