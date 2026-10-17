cmake_minimum_required(VERSION 3.15)
project(test_libenvpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libenvpp REQUIRED)

add_executable(test_libenvpp test.cpp)
set_property(TARGET test_libenvpp PROPERTY CXX_STANDARD 17)
target_link_libraries(test_libenvpp libenvpp::libenvpp)

enable_testing()
add_test(NAME test_libenvpp COMMAND test_libenvpp)