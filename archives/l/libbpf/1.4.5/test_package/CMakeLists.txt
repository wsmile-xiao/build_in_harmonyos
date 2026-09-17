cmake_minimum_required(VERSION 3.15)
project(test_libbpf C)

# Find the package via Conan-generated CMakeDeps
find_package(libbpf REQUIRED)

add_executable(test_libbpf test.c)
target_link_libraries(test_libbpf libbpf::libbpf)

enable_testing()
add_test(NAME test_libbpf COMMAND test_libbpf)
