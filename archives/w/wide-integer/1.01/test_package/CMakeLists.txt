cmake_minimum_required(VERSION 3.15)
project(test_wide_integer CXX)

# Find the package via Conan-generated CMakeDeps
find_package(wide-integer REQUIRED)

add_executable(test_wide_integer test.cpp)
target_link_libraries(test_wide_integer wide-integer::wide-integer)
target_compile_features(test_wide_integer PRIVATE cxx_std_20)

enable_testing()
add_test(NAME test_wide_integer COMMAND test_wide_integer)
