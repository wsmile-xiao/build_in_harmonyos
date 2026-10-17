cmake_minimum_required(VERSION 3.15)
project(test_conjure_enum CXX)

# Find the package via Conan-generated CMakeDeps
find_package(conjure_enum REQUIRED)

add_executable(test_conjure_enum test.cpp)
target_link_libraries(test_conjure_enum conjure_enum::conjure_enum)
target_compile_features(test_conjure_enum PRIVATE cxx_std_20)

enable_testing()
add_test(NAME test_conjure_enum COMMAND test_conjure_enum)