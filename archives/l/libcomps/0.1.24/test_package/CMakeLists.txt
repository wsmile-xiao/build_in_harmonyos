cmake_minimum_required(VERSION 3.15)
project(test_libcomps LANGUAGES C)

find_package(libcomps REQUIRED)

add_executable(test_libcomps test_libcomps.c)
target_link_libraries(test_libcomps PRIVATE libcomps::libcomps)

enable_testing()
add_test(NAME test_libcomps COMMAND test_libcomps)
