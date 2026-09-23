cmake_minimum_required(VERSION 3.15)
project(test_kbaloo CXX)

find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(KF6Baloo REQUIRED)

add_executable(test_kbaloo test.cpp)
target_link_libraries(test_kbaloo KF6::Baloo Qt6::Core)

enable_testing()
add_test(NAME test_kbaloo COMMAND test_kbaloo)
