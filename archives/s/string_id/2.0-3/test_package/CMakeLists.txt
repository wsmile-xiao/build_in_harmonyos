cmake_minimum_required(VERSION 3.15)
project(string_id_test_package LANGUAGES CXX)

find_package(foonathan_string_id CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_compile_features(test_package PRIVATE cxx_std_11)
target_link_libraries(test_package PRIVATE foonathan_string_id::foonathan_string_id)

enable_testing()
add_test(NAME string_id_consumer COMMAND test_package)
