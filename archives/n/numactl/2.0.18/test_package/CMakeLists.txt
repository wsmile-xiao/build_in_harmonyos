cmake_minimum_required(VERSION 3.15)
project(test_numactl C)

# Find the package via Conan-generated CMakeDeps
find_package(numactl REQUIRED)

add_executable(test_numactl test.c)
target_link_libraries(test_numactl numactl::numactl)

enable_testing()
add_test(NAME test_numactl COMMAND test_numactl)
