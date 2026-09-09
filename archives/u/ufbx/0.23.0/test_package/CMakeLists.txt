cmake_minimum_required(VERSION 3.15)
project(test_ufbx C)

# Find the package via Conan-generated CMakeDeps
find_package(ufbx REQUIRED)

add_executable(test_ufbx test.c)
target_link_libraries(test_ufbx ufbx::ufbx)

enable_testing()
add_test(NAME test_ufbx COMMAND test_ufbx)
