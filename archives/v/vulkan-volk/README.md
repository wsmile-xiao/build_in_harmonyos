# vulkan-volk

volk is a meta-loader for Vulkan. It allows applications to use Vulkan without linking against a specific Vulkan loader, providing function pointers for all Vulkan entry points.

## Description

volk simplifies Vulkan application development by:
- Loading the Vulkan loader dynamically at runtime (`volkInitialize()`)
- Providing all Vulkan function pointers (core + extensions) without explicit linking
- Supporting both instance-level and device-level function loading
- Offering header-only mode (`VOLK_HEADERS_ONLY`) for minimal overhead
- Supporting a C++ namespace mode (`VOLK_NAMESPACE`) for namespaced `vk*` functions

## Compiled Version
- 1.4.350 (2026-05-25)

## Dependencies
- vulkan-headers (vulkan-sdk-1.4.350.0)

## OHOS Adaptation

### Key Changes
1. **Platform/HarmonyOS.cmake**: Added to `cmake/Platform/` directory to suppress CMake "Unknown system" warning
2. **CMakeLists.txt**: Modified to prepend project cmake dir to `CMAKE_MODULE_PATH` and auto-set `VOLK_STATIC_DEFINES=VK_USE_PLATFORM_OHOS` for HarmonyOS builds using `CMAKE_HOST_SYSTEM_NAME`

### Include Path Behavior

volk.h provides two include modes:

**Header-only mode (default path)**:
```c
#include <volk.h>  // includes vulkan/vk_platform.h + vulkan/vulkan_core.h
```
When `VK_USE_PLATFORM_OHOS` is defined, volk.h also includes:
```c
#include <vulkan/vulkan_ohos.h>  // OHOS platform-specific Vulkan types
```

**Static library mode**:
```c
#include <volk.h>  // same headers, plus function pointer declarations
#include <volk.c>  // volk.c is installed as an include file, compiled into the application
```

When `VOLK_STATIC_DEFINES=VK_USE_PLATFORM_OHOS` is set, `VK_USE_PLATFORM_OHOS` is propagated as a compile definition to both `volk` and `volk_headers` targets, ensuring `vulkan/vulkan_ohos.h` is properly included through volk.h/volk.c.

## Usage

```cmake
find_package(volk REQUIRED)
target_link_libraries(myapp PRIVATE volk::volk)
```

Or header-only:
```cmake
find_package(volk REQUIRED)
target_link_libraries(myapp PRIVATE volk::volk_headers)
```