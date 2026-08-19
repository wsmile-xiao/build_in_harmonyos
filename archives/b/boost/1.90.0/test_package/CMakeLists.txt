cmake_minimum_required(VERSION 3.15)
project(test_boost CXX)

# Find the package via Conan-generated CMakeDeps, requesting the Boost.Test component.
# Canonical Boost naming: find_package(Boost COMPONENTS ...) + Boost::unit_test_framework.
find_package(Boost REQUIRED COMPONENTS unit_test_framework)

add_executable(test_boost test.cpp)
# Link the canonical Boost.Test CMake target exported by Conan
target_link_libraries(test_boost Boost::unit_test_framework)

enable_testing()
add_test(NAME test_boost COMMAND test_boost)
