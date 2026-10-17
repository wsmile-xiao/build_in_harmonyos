cmake_minimum_required(VERSION 3.15)
project(test_fermi-lite C)

# Find the package via Conan-generated CMakeDeps
find_package(fermi-lite REQUIRED)

add_executable(test_fermi-lite test.c)
target_link_libraries(test_fermi-lite fermi-lite::fermi-lite)

enable_testing()
add_test(NAME test_fermi-lite COMMAND test_fermi-lite)
