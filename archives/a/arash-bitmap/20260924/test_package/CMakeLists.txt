cmake_minimum_required(VERSION 3.15)
project(test_arash-bitmap CXX)

# Find the package via Conan-generated CMakeDeps
find_package(arash-bitmap REQUIRED)

add_executable(test_arash-bitmap test.cpp)
target_link_libraries(test_arash-bitmap arash-bitmap::arash-bitmap)

enable_testing()
add_test(NAME test_arash-bitmap COMMAND test_arash-bitmap)