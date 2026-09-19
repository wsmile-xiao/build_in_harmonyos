cmake_minimum_required(VERSION 3.15)
project(test_libscca C)

find_package(libscca REQUIRED)

add_executable(test_libscca test.c)
target_link_libraries(test_libscca libscca::libscca)

enable_testing()
add_test(NAME test_libscca COMMAND test_libscca)
