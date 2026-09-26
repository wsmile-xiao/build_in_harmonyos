cmake_minimum_required(VERSION 3.15)
project(test_libnu C)

find_package(nunicode REQUIRED)

add_executable(test_libnu test_libnu.c)
target_link_libraries(test_libnu nunicode::nu)

enable_testing()
add_test(NAME test_libnu COMMAND test_libnu)
