cmake_minimum_required(VERSION 3.15)
project(gulkan_test C)

find_package(gulkan REQUIRED CONFIG)

# The test also calls vkEnumerateInstanceExtensionProperties directly to
# prove the Vulkan loader path is real (R40). The OHOS loader is a system
# component; link it for this target only (never installed, no R26 concern).
find_library(VULKAN_LOADER_LIB NAMES vulkan PATHS /system/lib64 REQUIRED NO_DEFAULT_PATH)

add_executable(gulkan_test test.c)
target_link_libraries(gulkan_test PRIVATE gulkan::gulkan ${VULKAN_LOADER_LIB})

enable_testing()
add_test(NAME gulkan_test COMMAND gulkan_test)
