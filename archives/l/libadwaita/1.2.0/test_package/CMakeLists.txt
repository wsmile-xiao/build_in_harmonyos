cmake_minimum_required(VERSION 3.15)
project(test_libadwaita C)

# Find the package via Conan-generated CMakeDeps
find_package(libadwaita REQUIRED)

add_executable(test_libadwaita test.c)
target_link_libraries(test_libadwaita libadwaita::libadwaita)

enable_testing()
add_test(NAME test_libadwaita COMMAND test_libadwaita)
