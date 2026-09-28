cmake_minimum_required(VERSION 3.15)
project(test_xapian CXX)

find_package(xapian REQUIRED)

add_executable(test_xapian test_xapian.cpp)
target_link_libraries(test_xapian xapian::xapian)

enable_testing()
add_test(NAME test_xapian COMMAND test_xapian)
