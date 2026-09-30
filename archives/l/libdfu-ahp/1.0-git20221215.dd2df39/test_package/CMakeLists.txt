cmake_minimum_required(VERSION 3.15)
project(test_libdfu C)

find_package(libdfu CONFIG REQUIRED)

add_executable(test_libdfu test_libdfu.c)
target_link_libraries(test_libdfu PRIVATE libdfu::libdfu)

enable_testing()
add_test(NAME test_libdfu COMMAND test_libdfu)
