cmake_minimum_required(VERSION 3.15)
project(test_olm C)

# Find the package via Conan-generated CMakeDeps
find_package(olm REQUIRED)

add_executable(test_olm test.c)
target_link_libraries(test_olm olm::olm)

enable_testing()
add_test(NAME test_olm COMMAND test_olm)
