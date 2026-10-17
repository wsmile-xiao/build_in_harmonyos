cmake_minimum_required(VERSION 3.15)
project(test_libkaz C)

find_package(libkaz REQUIRED)

add_executable(test_libkaz test.c)
target_link_libraries(test_libkaz libkaz::libkaz)

enable_testing()
add_test(NAME test_libkaz COMMAND test_libkaz)
