cmake_minimum_required(VERSION 3.15)
project(test_libfyaml C)

# Find the package via Conan-generated CMakeDeps
find_package(libfyaml REQUIRED)

add_executable(test_libfyaml test.c)
target_link_libraries(test_libfyaml libfyaml::libfyaml)

enable_testing()
add_test(NAME test_libfyaml COMMAND test_libfyaml)