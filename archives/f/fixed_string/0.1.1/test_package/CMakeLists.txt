cmake_minimum_required(VERSION 3.15)
project(test_fixed_string CXX)

# Find the package via Conan-generated CMakeDeps
find_package(fixed_string REQUIRED)

add_executable(test_fixed_string test.cpp)
target_link_libraries(test_fixed_string fixed_string::fixed_string)
target_compile_features(test_fixed_string PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_fixed_string COMMAND test_fixed_string)
