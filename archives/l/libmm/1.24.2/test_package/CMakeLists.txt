cmake_minimum_required(VERSION 3.15)
project(test_mm C)

# Find the package via Conan-generated CMakeDeps
find_package(mm-glib REQUIRED)

add_executable(test_mm test_mm.c)
target_link_libraries(test_mm mm-glib::mm-glib)

enable_testing()
add_test(NAME test_mm COMMAND test_mm)
