cmake_minimum_required(VERSION 3.15)
project(test_sane-backends C)

# Find the package via Conan-generated CMakeDeps
find_package(sane-backends REQUIRED)

add_executable(test_sane-backends test.c)
target_link_libraries(test_sane-backends sane-backends::sane-backends)

enable_testing()
add_test(NAME test_sane-backends COMMAND test_sane-backends)
