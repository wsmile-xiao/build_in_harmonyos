cmake_minimum_required(VERSION 3.15)
project(nacl_test C CXX)

find_package(nacl REQUIRED)

add_executable(test_nacl test.c)
target_link_libraries(test_nacl PRIVATE nacl::nacl)

add_executable(test_nacl_cpp test.cpp)
target_link_libraries(test_nacl_cpp PRIVATE nacl::nacl)

enable_testing()
add_test(NAME test_nacl COMMAND test_nacl)
add_test(NAME test_nacl_cpp COMMAND test_nacl_cpp)
