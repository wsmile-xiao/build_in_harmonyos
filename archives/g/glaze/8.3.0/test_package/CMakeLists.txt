cmake_minimum_required(VERSION 3.15)
project(test_glaze LANGUAGES CXX)

# Glaze 8.3.0 requires C++23 (upstream target_compile_features cxx_std_23).
# CMake maps CXX_STANDARD 23 to -std=c++2b on clang <= 16.
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(glaze CONFIG REQUIRED)

add_executable(test_glaze test_glaze.cpp)
target_link_libraries(test_glaze PRIVATE glaze::glaze)

enable_testing()
add_test(NAME test_glaze COMMAND test_glaze)
