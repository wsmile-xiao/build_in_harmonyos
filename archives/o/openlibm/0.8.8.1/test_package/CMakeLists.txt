cmake_minimum_required(VERSION 3.15)
project(test_openlibm C)

# Find the package via Conan-generated CMakeDeps
find_package(openlibm REQUIRED)

add_executable(test_openlibm test.c)
target_link_libraries(test_openlibm openlibm::openlibm)

enable_testing()
add_test(NAME test_openlibm COMMAND test_openlibm)
