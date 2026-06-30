cmake_minimum_required(VERSION 3.15)
project(test_hickory-dns C)

# Find the package via Conan-generated CMakeDeps
find_package(hickory-dns REQUIRED)

add_executable(test_hickory-dns test.c)
target_link_libraries(test_hickory-dns hickory-dns::hickory-dns)

enable_testing()
add_test(NAME test_hickory-dns COMMAND test_hickory-dns)
