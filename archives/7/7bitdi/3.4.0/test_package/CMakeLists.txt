cmake_minimum_required(VERSION 3.15)
project(test_7bitdi CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(7bitdi REQUIRED CONFIG)

add_executable(test_7bitdi test.cpp)
target_link_libraries(test_7bitdi 7bitdi::7bitdi)

enable_testing()
add_test(NAME test_7bitdi COMMAND test_7bitdi)