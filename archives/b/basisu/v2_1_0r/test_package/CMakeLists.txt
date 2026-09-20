cmake_minimum_required(VERSION 3.15)
project(test_basisu CXX)

# Find the package via Conan-generated CMakeDeps
find_package(basisu REQUIRED)

add_executable(test_basisu basisu_test.cpp)
target_link_libraries(test_basisu basisu::basisu)

enable_testing()
add_test(NAME test_basisu COMMAND test_basisu)
