cmake_minimum_required(VERSION 3.15)
project(test_qdbm C)

# Find the package via Conan-generated CMakeDeps
find_package(qdbm REQUIRED)

add_executable(test_qdbm test.c)
target_link_libraries(test_qdbm qdbm::qdbm)

enable_testing()
add_test(NAME test_qdbm COMMAND test_qdbm)
