cmake_minimum_required(VERSION 3.15)
project(test_fir1 CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(fir1 REQUIRED CONFIG)

add_executable(test_fir1 test.cpp)
target_link_libraries(test_fir1 fir1::fir1)

enable_testing()
add_test(NAME test_fir1 COMMAND test_fir1)
