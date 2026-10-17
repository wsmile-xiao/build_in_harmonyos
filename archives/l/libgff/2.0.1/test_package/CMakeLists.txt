cmake_minimum_required(VERSION 3.15)
project(test_libgff CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libgff REQUIRED)

add_executable(test_libgff test.cpp)
target_link_libraries(test_libgff libgff::libgff)

enable_testing()
add_test(NAME test_libgff COMMAND test_libgff)
