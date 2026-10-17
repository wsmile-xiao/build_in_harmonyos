cmake_minimum_required(VERSION 3.15)
project(test_libcaes C)

find_package(libcaes CONFIG REQUIRED)

add_executable(test_libcaes test_libcaes.c)
target_link_libraries(test_libcaes PRIVATE libcaes::libcaes)

enable_testing()
add_test(NAME test_libcaes COMMAND test_libcaes)
