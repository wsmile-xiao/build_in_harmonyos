cmake_minimum_required(VERSION 3.15)
project(test_cni-plugin-flannel C)

# Find the package via Conan-generated CMakeDeps
find_package(cni-plugin-flannel REQUIRED)

add_executable(test_cni-plugin-flannel test.c)
target_link_libraries(test_cni-plugin-flannel cni-plugin-flannel::cni-plugin-flannel)

enable_testing()
add_test(NAME test_cni-plugin-flannel COMMAND test_cni-plugin-flannel)
