cmake_minimum_required(VERSION 3.15)
project(test_libxp C)

find_package(libxp REQUIRED)

add_executable(test_libxp test_libxp.c)
target_link_libraries(test_libxp PRIVATE libxp::libxp)

enable_testing()
add_test(NAME test_libxp COMMAND test_libxp)
