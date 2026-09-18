cmake_minimum_required(VERSION 3.15)
project(test_uvg266 C)

# Find the package via Conan-generated CMakeDeps
find_package(uvg266 REQUIRED)

add_executable(test_uvg266 test.c)
target_link_libraries(test_uvg266 uvg266::uvg266)

enable_testing()
add_test(NAME test_uvg266 COMMAND test_uvg266)
