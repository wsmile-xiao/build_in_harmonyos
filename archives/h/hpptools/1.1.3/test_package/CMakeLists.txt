cmake_minimum_required(VERSION 3.15)
project(test_hpptools CXX)

# Find the package via Conan-generated CMakeDeps
find_package(hpptools REQUIRED)

add_executable(test_hpptools test_package.cpp)
target_link_libraries(test_hpptools hpptools::hpptools)
target_compile_features(test_hpptools PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_hpptools COMMAND test_hpptools)
