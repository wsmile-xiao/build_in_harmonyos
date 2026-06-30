cmake_minimum_required(VERSION 3.15)
project(test_cni-plugins C)

# Find the package via Conan-generated CMakeDeps
find_package(cni-plugins REQUIRED)

add_executable(test_cni-plugins test.c)
target_link_libraries(test_cni-plugins cni-plugins::cni-plugins)

enable_testing()
add_test(NAME test_cni-plugins COMMAND test_cni-plugins)
