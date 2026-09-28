cmake_minimum_required(VERSION 3.15)
project(test_dslib C)

# Find the package via Conan-generated CMakeDeps
find_package(dslib REQUIRED)

add_executable(test_dslib test.c)
target_link_libraries(test_dslib dslib::dslib)

enable_testing()
add_test(NAME test_dslib COMMAND test_dslib)
