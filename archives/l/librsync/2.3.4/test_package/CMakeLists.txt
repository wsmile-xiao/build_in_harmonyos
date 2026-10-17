cmake_minimum_required(VERSION 3.15)
project(test_librsync C)

find_package(librsync REQUIRED CONFIG)

add_executable(test_librsync test_librsync.c)
target_link_libraries(test_librsync PRIVATE librsync::librsync)

enable_testing()
add_test(NAME test_librsync COMMAND test_librsync)
