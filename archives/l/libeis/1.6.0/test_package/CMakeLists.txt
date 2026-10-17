cmake_minimum_required(VERSION 3.15)
project(test_libeis C)

find_package(libeis REQUIRED)

add_executable(test_libeis src/test_package.c)
target_link_libraries(test_libeis libeis::libeis)

enable_testing()
add_test(NAME test_libeis COMMAND test_libeis)
