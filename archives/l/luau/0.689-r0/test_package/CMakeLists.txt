cmake_minimum_required(VERSION 3.15)
project(test_luau CXX)

find_package(luau REQUIRED)

add_executable(test_luau test.cpp)
target_link_libraries(test_luau luau::luau)

enable_testing()
add_test(NAME test_luau COMMAND test_luau)
