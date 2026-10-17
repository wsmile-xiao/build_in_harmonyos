cmake_minimum_required(VERSION 3.16)
project(test_libmill C)

enable_testing()

find_package(libmill REQUIRED)

add_executable(test_libmill src/test_libmill.c)
target_link_libraries(test_libmill libmill::libmill)

add_test(NAME libmill_consumer COMMAND test_libmill)
