cmake_minimum_required(VERSION 3.15)
project(test_mac CXX)

# Find the package via Conan-generated CMakeDeps
find_package(mac REQUIRED)

add_executable(test_mac test.cpp)
target_link_libraries(test_mac mac::mac)

enable_testing()
add_test(NAME test_mac COMMAND test_mac)
