cmake_minimum_required(VERSION 3.15)
project(test_libgsm C)

# Find the package via Conan-generated CMakeDeps
find_package(libgsm REQUIRED)

add_executable(test_libgsm test.c)
target_link_libraries(test_libgsm libgsm::libgsm)

enable_testing()
add_test(NAME test_libgsm COMMAND test_libgsm)
