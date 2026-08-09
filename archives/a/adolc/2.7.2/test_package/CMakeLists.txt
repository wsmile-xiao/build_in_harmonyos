cmake_minimum_required(VERSION 3.15)
project(test_adolc CXX)

# Find the package via Conan-generated CMakeDeps
find_package(adolc REQUIRED)

add_executable(test_adolc test.cpp)
target_link_libraries(test_adolc adolc::adolc)

enable_testing()
add_test(NAME test_adolc COMMAND test_adolc)
