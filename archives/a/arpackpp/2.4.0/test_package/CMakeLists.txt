cmake_minimum_required(VERSION 3.15)
project(test_arpackpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(arpackpp REQUIRED)

add_executable(test_arpackpp src/test.cpp)

# arpackpp provides transitive deps on arpack-ng, openblas, lapack
target_link_libraries(test_arpackpp arpackpp::arpackpp)

enable_testing()
add_test(NAME test_arpackpp COMMAND test_arpackpp)
