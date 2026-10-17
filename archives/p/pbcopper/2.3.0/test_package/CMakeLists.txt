cmake_minimum_required(VERSION 3.15)
project(test_pbcopper CXX)

find_package(pbcopper REQUIRED)

add_executable(test_pbcopper test_pbcopper.cpp)
target_link_libraries(test_pbcopper pbcopper::pbcopper)

enable_testing()
add_test(NAME test_pbcopper COMMAND test_pbcopper)
