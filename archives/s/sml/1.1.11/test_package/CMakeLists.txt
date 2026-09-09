cmake_minimum_required(VERSION 3.15)
project(test_sml CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(sml REQUIRED CONFIG)

add_executable(test_sml test.cpp)
target_link_libraries(test_sml sml::sml)

enable_testing()
add_test(NAME test_sml COMMAND test_sml)