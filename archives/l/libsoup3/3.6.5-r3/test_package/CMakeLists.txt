cmake_minimum_required(VERSION 3.15)
project(test_libsoup3 C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=libsoup-3.0).
find_package(libsoup-3.0 CONFIG REQUIRED)

add_executable(test_libsoup3 test.c)
target_link_libraries(test_libsoup3 libsoup-3.0::libsoup-3.0)

enable_testing()
add_test(NAME test_libsoup3 COMMAND test_libsoup3)
