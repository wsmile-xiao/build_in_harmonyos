cmake_minimum_required(VERSION 3.15)
project(test_rapidfuzz_cpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(rapidfuzz REQUIRED)

add_executable(test_rapidfuzz_cpp test.cpp)
target_link_libraries(test_rapidfuzz_cpp rapidfuzz::rapidfuzz)

enable_testing()
add_test(NAME test_rapidfuzz_cpp COMMAND test_rapidfuzz_cpp)