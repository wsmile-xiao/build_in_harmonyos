cmake_minimum_required(VERSION 3.15)
project(test_farmhash CXX)

# Find the package via Conan-generated CMakeDeps
find_package(farmhash REQUIRED)

add_executable(test_farmhash test.cpp)
target_link_libraries(test_farmhash farmhash::farmhash)

enable_testing()
add_test(NAME test_farmhash COMMAND test_farmhash)
