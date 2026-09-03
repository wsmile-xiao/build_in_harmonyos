cmake_minimum_required(VERSION 3.15)
project(test_libtatsu C CXX)

include(CTest)
find_package(libtatsu-1.0 REQUIRED)
find_package(libplist-2.0 REQUIRED)

# Main consumer test: offline verification of the TSS request/response
# contract against a local mock HTTP server (127.0.0.1), including
# serialization, response parsing and negative paths.
add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE libtatsu::libtatsu libplist::libplist)
add_test(NAME test_package COMMAND test_package)

# C++ consumer: the public headers declare extern "C", verify a C++
# translation unit can include them, link and call the API.
add_executable(test_cpp test_cpp.cpp)
target_link_libraries(test_cpp PRIVATE libtatsu::libtatsu libplist::libplist)
add_test(NAME test_cpp COMMAND test_cpp)
