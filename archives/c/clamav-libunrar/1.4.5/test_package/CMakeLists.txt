cmake_minimum_required(VERSION 3.15)
project(test_clamav_libunrar CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(clamav-libunrar REQUIRED)

add_executable(test_clamav_libunrar test_clamav_libunrar.cpp)
target_link_libraries(test_clamav_libunrar clamav-libunrar::clamunrar)

enable_testing()
add_test(NAME test_clamav_libunrar COMMAND test_clamav_libunrar)
