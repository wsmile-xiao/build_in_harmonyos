cmake_minimum_required(VERSION 3.15)
project(test_libsimdpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libsimdpp REQUIRED)

add_executable(test_libsimdpp test.cpp)
target_link_libraries(test_libsimdpp libsimdpp::libsimdpp)

enable_testing()
add_test(NAME test_libsimdpp COMMAND test_libsimdpp)