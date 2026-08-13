cmake_minimum_required(VERSION 3.15)
project(test_orocos-kdl CXX)

# Find the package via Conan-generated CMakeDeps
find_package(orocos-kdl REQUIRED)

add_executable(test_orocos-kdl test.cpp)
target_link_libraries(test_orocos-kdl orocos-kdl::orocos-kdl)

enable_testing()
add_test(NAME test_orocos-kdl COMMAND test_orocos-kdl)