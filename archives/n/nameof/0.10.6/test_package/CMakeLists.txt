cmake_minimum_required(VERSION 3.15)
project(test_nameof CXX)

find_package(nameof REQUIRED)

add_executable(test_nameof test.cpp)
target_link_libraries(test_nameof PRIVATE nameof::nameof)
target_compile_features(test_nameof PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_nameof COMMAND test_nameof)
