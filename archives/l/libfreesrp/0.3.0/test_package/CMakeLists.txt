cmake_minimum_required(VERSION 3.15)
project(test_freesrp CXX)

set(CMAKE_CXX_STANDARD 11)

# Find the package via Conan-generated CMakeDeps
find_package(freesrp REQUIRED)

add_executable(test_freesrp test_freesrp.cpp)
target_link_libraries(test_freesrp freesrp::freesrp)

enable_testing()
add_test(NAME test_freesrp COMMAND test_freesrp)
