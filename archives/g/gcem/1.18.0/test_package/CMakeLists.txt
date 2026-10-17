cmake_minimum_required(VERSION 3.15)
project(test_gcem LANGUAGES CXX)

# Find the package via Conan-generated CMakeDeps
find_package(gcem CONFIG REQUIRED)

add_executable(test_gcem test.cpp)
target_compile_features(test_gcem PRIVATE cxx_std_11)
target_link_libraries(test_gcem PRIVATE gcem::gcem)

enable_testing()
add_test(NAME test_gcem COMMAND test_gcem)
