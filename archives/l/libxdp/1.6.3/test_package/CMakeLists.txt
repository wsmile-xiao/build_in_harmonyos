cmake_minimum_required(VERSION 3.15)
project(test_libxdp C)

find_package(libxdp REQUIRED)

add_executable(test_libxdp test.c)
target_link_libraries(test_libxdp libxdp::libxdp)

enable_testing()
add_test(NAME test_libxdp COMMAND test_libxdp)
