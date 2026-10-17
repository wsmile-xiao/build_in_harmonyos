cmake_minimum_required(VERSION 3.15)
project(test_sigar LANGUAGES C)

find_package(sigar REQUIRED)

add_executable(test_sigar test_sigar.c)
target_link_libraries(test_sigar sigar::sigar)

enable_testing()
add_test(NAME test_sigar COMMAND test_sigar)
