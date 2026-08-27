cmake_minimum_required(VERSION 3.15)
project(test_vulkan-tools C)

add_executable(test_vulkan-tools test.c)

enable_testing()
add_test(NAME test_vulkan-tools COMMAND test_vulkan-tools)
