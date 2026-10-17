cmake_minimum_required(VERSION 3.15)
project(test_shim CXX)

# Find the package via Conan-generated CMakeDeps
find_package(quickcpplib REQUIRED)

add_executable(test_shim test_shim.cpp)
target_link_libraries(test_shim quickcpplib::quickcpplib)
set_target_properties(test_shim PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_shim COMMAND test_shim)
