cmake_minimum_required(VERSION 3.15)
project(test_kissfft C)

# Find the package via Conan-generated CMakeDeps
find_package(kissfft REQUIRED)

add_executable(test_kissfft test.c)
target_link_libraries(test_kissfft kissfft::kissfft)

enable_testing()
add_test(NAME test_kissfft COMMAND test_kissfft)
