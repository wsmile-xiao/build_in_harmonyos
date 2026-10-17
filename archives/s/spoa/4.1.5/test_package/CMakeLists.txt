cmake_minimum_required(VERSION 3.15)
project(test_spoa CXX)

# Find the package via Conan-generated CMakeDeps
find_package(spoa REQUIRED)

add_executable(test_spoa test.cpp)
target_link_libraries(test_spoa spoa::spoa)

enable_testing()
add_test(NAME test_spoa COMMAND test_spoa)