cmake_minimum_required(VERSION 3.15)
project(test_fast-cdr CXX)

# Find the package via Conan-generated CMakeDeps
find_package(fastcdr REQUIRED)

add_executable(test_fast-cdr test_package.cpp)
target_link_libraries(test_fast-cdr fastcdr::fastcdr)

enable_testing()
add_test(NAME test_fast-cdr COMMAND test_fast-cdr)
