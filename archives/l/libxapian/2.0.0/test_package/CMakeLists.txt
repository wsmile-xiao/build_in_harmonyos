cmake_minimum_required(VERSION 3.15)
project(test_libxapian CXX)

find_package(xapian REQUIRED)

add_executable(test_libxapian test_libxapian.cpp)
target_link_libraries(test_libxapian xapian::xapian)

enable_testing()
add_test(NAME test_libxapian COMMAND test_libxapian)
