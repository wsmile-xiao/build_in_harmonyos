cmake_minimum_required(VERSION 3.15)
project(test_skypat CXX)

# Find the package via Conan-generated CMakeDeps
find_package(skypat REQUIRED)

add_executable(test_skypat test_skypat.cpp)
target_link_libraries(test_skypat skypat::skypat)
set_property(TARGET test_skypat PROPERTY CXX_STANDARD 11)
set_property(TARGET test_skypat PROPERTY CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_skypat COMMAND test_skypat)
