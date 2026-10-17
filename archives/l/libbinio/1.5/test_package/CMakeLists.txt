cmake_minimum_required(VERSION 3.15)
project(test_libbinio CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libbinio REQUIRED)

add_executable(test_libbinio test.cpp)
target_link_libraries(test_libbinio libbinio::libbinio)

enable_testing()
add_test(NAME test_libbinio COMMAND test_libbinio)
