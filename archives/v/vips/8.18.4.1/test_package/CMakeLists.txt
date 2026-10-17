cmake_minimum_required(VERSION 3.15)
project(test_vips C)

find_package(vips REQUIRED)

add_executable(test_vips test.c)
target_link_libraries(test_vips PRIVATE vips::vips)

enable_testing()
add_test(NAME test_vips COMMAND test_vips)
