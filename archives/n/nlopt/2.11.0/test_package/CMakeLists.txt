cmake_minimum_required(VERSION 3.15)
project(test_nlopt CXX)

# Find the package via Conan-generated CMakeDeps
find_package(nlopt REQUIRED)

add_executable(test_nlopt test.cpp)
target_link_libraries(test_nlopt nlopt::nlopt)

enable_testing()
add_test(NAME test_nlopt COMMAND test_nlopt)
