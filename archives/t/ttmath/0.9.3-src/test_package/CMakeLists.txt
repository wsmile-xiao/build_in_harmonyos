cmake_minimum_required(VERSION 3.15)
project(test_ttmath CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ttmath REQUIRED)

add_executable(test_ttmath test.cpp)
target_link_libraries(test_ttmath PRIVATE ttmath::ttmath)
target_compile_features(test_ttmath PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_ttmath COMMAND test_ttmath)
