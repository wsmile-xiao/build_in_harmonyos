cmake_minimum_required(VERSION 3.15)
project(test_verdict CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(verdict REQUIRED)

add_executable(test_verdict test_verdict.cpp)
target_link_libraries(test_verdict verdict::verdict)

enable_testing()
add_test(NAME test_verdict COMMAND test_verdict)
