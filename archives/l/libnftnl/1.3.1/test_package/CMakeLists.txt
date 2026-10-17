cmake_minimum_required(VERSION 3.15)
project(test_libnftnl C)

# Find the package via Conan-generated CMakeDeps
find_package(libnftnl REQUIRED)

add_executable(test_libnftnl test.c)
target_link_libraries(test_libnftnl libnftnl::libnftnl)

enable_testing()
add_test(NAME test_libnftnl COMMAND test_libnftnl)
