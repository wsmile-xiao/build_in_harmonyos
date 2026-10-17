cmake_minimum_required(VERSION 3.15)
project(test_type_lite CXX)

# Find the package via Conan-generated CMakeDeps
find_package(type-lite REQUIRED)

add_executable(test_type_lite test.cpp)
target_link_libraries(test_type_lite nonstd::type-lite)
target_compile_features(test_type_lite PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_type_lite COMMAND test_type_lite)