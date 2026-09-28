cmake_minimum_required(VERSION 3.15)
project(test_libdxfrw CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libdxfrw REQUIRED)

add_executable(test_libdxfrw test.cpp)
target_link_libraries(test_libdxfrw libdxfrw::libdxfrw)

enable_testing()
add_test(NAME test_libdxfrw COMMAND test_libdxfrw)
