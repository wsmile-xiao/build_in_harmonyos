cmake_minimum_required(VERSION 3.15)
project(test_libcutl CXX)

find_package(libcutl REQUIRED)

add_executable(test_libcutl test.cpp)
target_link_libraries(test_libcutl libcutl::libcutl)

enable_testing()
add_test(NAME test_libcutl COMMAND test_libcutl)
