cmake_minimum_required(VERSION 3.15)
project(test_args-parser CXX)

# Find the package via Conan-generated CMakeDeps
find_package(args-parser REQUIRED)

add_executable(test_args-parser test.cpp)
target_link_libraries(test_args-parser args-parser::args-parser)
target_compile_features(test_args-parser PRIVATE cxx_std_14)

enable_testing()
add_test(NAME test_args-parser COMMAND test_args-parser)