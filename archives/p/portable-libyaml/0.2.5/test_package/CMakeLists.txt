cmake_minimum_required(VERSION 3.15)
project(test_portable_libyaml C)

# Find the package via Conan-generated CMakeDeps
find_package(yaml REQUIRED)

add_executable(test_portable_libyaml test.c)
target_link_libraries(test_portable_libyaml yaml)

enable_testing()
add_test(NAME test_portable_libyaml COMMAND test_portable_libyaml)
