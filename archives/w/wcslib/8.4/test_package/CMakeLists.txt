cmake_minimum_required(VERSION 3.15)
project(test_wcslib C)

# Find the package via Conan-generated CMakeDeps
find_package(wcslib REQUIRED)

add_executable(test_wcslib test.c)
target_link_libraries(test_wcslib wcslib::wcslib)

enable_testing()
add_test(NAME test_wcslib COMMAND test_wcslib)
