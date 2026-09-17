cmake_minimum_required(VERSION 3.15)
project(test_libsoup C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=libsoup-2.4).
find_package(libsoup-2.4 CONFIG REQUIRED)

add_executable(test_libsoup test.c)
target_link_libraries(test_libsoup libsoup-2.4::libsoup-2.4)

enable_testing()
add_test(NAME test_libsoup COMMAND test_libsoup)
