cmake_minimum_required(VERSION 3.15)
project(test_x86-simd-sort CXX)

# Find the package via Conan-generated CMakeDeps
find_package(x86-simd-sort REQUIRED)

add_executable(test_x86-simd-sort test.cpp)
target_link_libraries(test_x86-simd-sort x86-simd-sort::x86-simd-sort)
target_compile_features(test_x86-simd-sort PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_x86-simd-sort COMMAND test_x86-simd-sort)