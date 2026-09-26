cmake_minimum_required(VERSION 3.15)
project(test_gplotpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(gplotpp REQUIRED)

add_executable(test_gplotpp test.cpp)
target_link_libraries(test_gplotpp gplotpp::gplotpp)

enable_testing()
add_test(NAME test_gplotpp COMMAND test_gplotpp)