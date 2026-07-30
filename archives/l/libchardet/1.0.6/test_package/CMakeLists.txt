cmake_minimum_required(VERSION 3.15)
project(test_libchardet CXX)

find_package(libchardet REQUIRED)

add_executable(test_libchardet test_libchardet.cpp)
target_link_libraries(test_libchardet PRIVATE libchardet::libchardet)

enable_testing()
add_test(NAME test_libchardet COMMAND test_libchardet)
