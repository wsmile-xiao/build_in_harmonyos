cmake_minimum_required(VERSION 3.15)
project(test_cpp_can_parser CXX)

# Find the package via Conan-generated CMakeDeps (config keeps the dash name)
find_package(cpp-can-parser CONFIG REQUIRED)

add_executable(test_consumer test_consumer.cpp)
target_link_libraries(test_consumer cpp-can-parser::cpp-can-parser)

add_executable(harmonyos_specific_test harmonyos_specific_test.cpp)
target_link_libraries(harmonyos_specific_test cpp-can-parser::cpp-can-parser)
