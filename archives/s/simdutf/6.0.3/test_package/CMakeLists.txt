cmake_minimum_required(VERSION 3.15)
project(test_simdutf CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(simdutf REQUIRED)

add_executable(test_simdutf test_package.cpp)
target_link_libraries(test_simdutf simdutf::simdutf)

enable_testing()
add_test(NAME test_simdutf COMMAND test_simdutf)