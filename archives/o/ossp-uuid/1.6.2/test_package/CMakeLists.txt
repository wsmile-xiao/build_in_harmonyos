cmake_minimum_required(VERSION 3.15)
project(test_ossp-uuid C)

# Find the package via Conan-generated CMakeDeps
find_package(ossp-uuid REQUIRED)

add_executable(test_ossp-uuid test.c)
target_link_libraries(test_ossp-uuid ossp-uuid::ossp-uuid)

enable_testing()
add_test(NAME test_ossp-uuid COMMAND test_ossp-uuid)
