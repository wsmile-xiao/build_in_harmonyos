cmake_minimum_required(VERSION 3.15)
project(test_libtasn1 C)

find_package(libtasn1 REQUIRED)

add_executable(test_libtasn1 test.c)
target_link_libraries(test_libtasn1 libtasn1::libtasn1)

enable_testing()
add_test(NAME test_libtasn1 COMMAND test_libtasn1)
