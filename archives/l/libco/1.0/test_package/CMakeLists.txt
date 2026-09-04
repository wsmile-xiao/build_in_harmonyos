cmake_minimum_required(VERSION 3.15)
project(test_libco CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libco REQUIRED)

add_executable(test_libco test.cpp)
target_link_libraries(test_libco PRIVATE libco::libco)

enable_testing()
add_test(NAME test_libco COMMAND test_libco)
