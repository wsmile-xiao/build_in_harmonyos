cmake_minimum_required(VERSION 3.15)
project(test_vulkan_loader C)

find_package(Vulkan REQUIRED)

add_executable(test_vulkan_loader test_package.c)
target_link_libraries(test_vulkan_loader Vulkan::Vulkan)

enable_testing()
add_test(NAME test_vulkan_loader COMMAND test_vulkan_loader)
