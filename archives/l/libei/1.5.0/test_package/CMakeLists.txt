cmake_minimum_required(VERSION 3.15)
project(test_libei C)

find_package(libei REQUIRED)

add_executable(test_libei src/test_package.c)
target_link_libraries(test_libei libei::libei)

enable_testing()
add_test(NAME test_libei COMMAND test_libei)
