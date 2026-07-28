cmake_minimum_required(VERSION 3.15)
project(test_xtensor CXX)

find_package(xtl REQUIRED)
find_package(xsimd REQUIRED)
find_package(xtensor REQUIRED)

add_executable(test_xtensor test.cpp)
target_link_libraries(test_xtensor PRIVATE xtensor xtl xsimd)

enable_testing()
add_test(NAME test_xtensor COMMAND test_xtensor)
