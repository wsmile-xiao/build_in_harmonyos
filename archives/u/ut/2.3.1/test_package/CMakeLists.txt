cmake_minimum_required(VERSION 3.15)
project(test_ut CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ut REQUIRED)

add_executable(test_ut test.cpp)
target_link_libraries(test_ut ut::ut)
target_compile_features(test_ut PRIVATE cxx_std_20)

enable_testing()
add_test(NAME test_ut COMMAND test_ut)
