cmake_minimum_required(VERSION 3.14)
project(test_libinstpatch C)

find_package(libinstpatch REQUIRED)

add_executable(test_libinstpatch test_libinstpatch.c)
target_link_libraries(test_libinstpatch libinstpatch::libinstpatch)

enable_testing()
add_test(NAME libinstpatch_test COMMAND test_libinstpatch)
