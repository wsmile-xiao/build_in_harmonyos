cmake_minimum_required(VERSION 3.15)
project(test_argagg CXX)

# Find the package via Conan-generated CMakeDeps
find_package(argagg REQUIRED)

add_executable(test_argagg test.cpp)
target_link_libraries(test_argagg argagg::argagg)
target_compile_features(test_argagg PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_argagg COMMAND test_argagg)
