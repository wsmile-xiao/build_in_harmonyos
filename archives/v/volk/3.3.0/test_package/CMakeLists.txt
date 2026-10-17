cmake_minimum_required(VERSION 3.15)
project(test_volk C)

# Conan CMakeDeps resolves the package through the exported
# lib/cmake/volk/VolkConfig.cmake (target Volk::volk).
find_package(Volk REQUIRED)

add_executable(test_volk test.c)
target_link_libraries(test_volk Volk::volk)

enable_testing()
add_test(NAME test_volk COMMAND test_volk)
