cmake_minimum_required(VERSION 3.15)
project(test_dylib CXX)

# Find the package via Conan-generated CMakeDeps
find_package(dylib REQUIRED)

add_executable(test_dylib test.cpp)
target_link_libraries(test_dylib dylib::dylib)
set_target_properties(test_dylib PROPERTIES CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_dylib COMMAND test_dylib)
