cmake_minimum_required(VERSION 3.15)
project(test_fmtlog CXX)

# Find the package via Conan-generated CMakeDeps
find_package(fmtlog REQUIRED)

add_executable(test_fmtlog test.cpp)
target_link_libraries(test_fmtlog fmtlog::fmtlog)

enable_testing()
add_test(NAME test_fmtlog COMMAND test_fmtlog)
