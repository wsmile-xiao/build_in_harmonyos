cmake_minimum_required(VERSION 3.15)
project(test_mpmcqueue CXX)

# Find the package via Conan-generated CMakeDeps
find_package(mpmcqueue REQUIRED)

add_executable(test_mpmcqueue test.cpp)
target_link_libraries(test_mpmcqueue mpmcqueue::mpmcqueue)

enable_testing()
add_test(NAME test_mpmcqueue COMMAND test_mpmcqueue)