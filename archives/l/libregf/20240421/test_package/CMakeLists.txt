cmake_minimum_required(VERSION 3.15)
project(test_libregf C)

find_package(libregf REQUIRED)

add_executable(test_libregf test.c)
target_link_libraries(test_libregf libregf::libregf)

enable_testing()
add_test(NAME test_libregf COMMAND test_libregf)
