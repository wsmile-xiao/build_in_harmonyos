# vulkan-utility-libraries

Vulkan Utility Libraries provide utility functionality for Vulkan developers, including:

- **VulkanLayerSettings**: Library for managing Vulkan layer settings
- **VulkanSafeStruct**: Library providing safe structure utilities for Vulkan
- **VulkanUtilityHeaders**: Header-only utility components for Vulkan

These libraries are part of the Vulkan SDK and serve as building blocks for Vulkan validation layers and other Vulkan tools.

## Version

- **vulkan-sdk-1.4.350.0**: Latest Vulkan SDK utility libraries release

## Dependencies

- C++17 compiler (clang 15+)
- CMake 3.14+
- Vulkan Headers (runtime dependency for some features)

## Build Notes

- Build system: cmake
- No test targets in CMakeLists.txt (library-only project)
- Produces static libraries: libVulkanLayerSettings.a, libVulkanSafeStruct.a