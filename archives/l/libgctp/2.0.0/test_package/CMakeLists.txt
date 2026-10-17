cmake_minimum_required(VERSION 3.15)
project(test_libgctp C)

find_package(libgctp REQUIRED)

add_executable(test_libgctp test.c)
target_link_libraries(test_libgctp libgctp::libgctp)

enable_testing()
add_test(NAME test_libgctp COMMAND test_libgctp)
