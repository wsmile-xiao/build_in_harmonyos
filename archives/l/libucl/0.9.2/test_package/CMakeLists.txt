cmake_minimum_required(VERSION 3.15)
project(test_libucl C)

find_package(ucl CONFIG REQUIRED)

add_executable(test_libucl test.c)
target_link_libraries(test_libucl PRIVATE ucl::ucl)

enable_testing()
add_test(NAME test_libucl COMMAND test_libucl)
