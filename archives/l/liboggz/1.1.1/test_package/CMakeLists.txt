cmake_minimum_required(VERSION 3.15)
project(test_liboggz C)

# Find the package via Conan-generated CMakeDeps
find_package(liboggz REQUIRED)
find_package(libogg REQUIRED)

add_executable(test_liboggz test.c)
target_link_libraries(test_liboggz liboggz::liboggz libogg::libogg)

enable_testing()
add_test(NAME test_liboggz COMMAND test_liboggz)
