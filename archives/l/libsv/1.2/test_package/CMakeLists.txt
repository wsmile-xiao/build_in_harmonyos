cmake_minimum_required(VERSION 3.15)
project(test_libsv C)

find_package(libsv REQUIRED)

add_executable(test_sv test_sv.c)
target_link_libraries(test_sv libsv::libsv)

enable_testing()
add_test(NAME test_sv COMMAND test_sv)
