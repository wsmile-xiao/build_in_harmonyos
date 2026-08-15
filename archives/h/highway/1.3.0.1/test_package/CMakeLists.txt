cmake_minimum_required(VERSION 3.15)
project(test_highway CXX)

find_package(hwy REQUIRED)

add_executable(test_highway test_highway.cpp)
target_link_libraries(test_highway PRIVATE hwy::hwy)
target_compile_features(test_highway PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_highway COMMAND test_highway)
