cmake_minimum_required(VERSION 3.15)
project(test_vulkan_headers C)

find_package(VulkanHeaders REQUIRED)

add_executable(test_vulkan_headers test_package.c)
target_link_libraries(test_vulkan_headers Vulkan::Headers)

enable_testing()
add_test(NAME test_vulkan_headers COMMAND test_vulkan_headers)
