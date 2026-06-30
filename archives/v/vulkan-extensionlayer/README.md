# vulkan-extensionlayer

Vulkan Extension Layer provides implementations of Vulkan extensions that are not natively supported by the underlying driver or platform, delivered as Vulkan layers.

## Description

Vulkan Extension Layer allows applications to use newer Vulkan extensions on devices with older drivers by:
- Providing VK_KHR_synchronization2 extension as a layer (VkLayer_khronos_synchronization2)
- Providing VK_EXT_shader_object extension as a layer (VkLayer_khronos_shader_object)
- Providing timeline semaphore emulation as a layer (VkLayer_khronos_timeline_semaphore)
- Loading automatically via VK_INSTANCE_LAYERS or explicit layer manifests

## Compiled Version
- 1.4.350 (2026-05-25)

## Dependencies
- vulkan-headers (vulkan-sdk-1.4.350.0)
- vulkan-utility-libraries (vulkan-sdk-1.4.350.0)
- vulkan-volk (1.4.350)

## OHOS Adaptation

### Key Changes
1. **layers/CMakeLists.txt**: Changed `if (UNIX)` condition to `if (UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")` to enable JSON layer manifest installation on HarmonyOS, since CMake does not set the UNIX variable on HarmonyOS (missing Platform/HarmonyOS module)
2. **WSI disabled**: Explicitly disabled BUILD_WSI_XCB_SUPPORT, BUILD_WSI_XLIB_SUPPORT, BUILD_WSI_WAYLAND_SUPPORT since HarmonyOS has no X11/Wayland display system

### Generated Vulkan Layers

| Layer | .so File | JSON Manifest | Description |
|-------|----------|---------------|-------------|
| VK_LAYER_KHRONOS_synchronization2 | libVkLayer_khronos_synchronization2.so | VkLayer_khronos_synchronization2.json | VK_KHR_synchronization2 extension |
| VK_LAYER_KHRONOS_shader_object | libVkLayer_khronos_shader_object.so | VkLayer_khronos_shader_object.json | VK_EXT_shader_object extension |
| VK_LAYER_KHRONOS_timeline_semaphore | libVkLayer_khronos_timeline_semaphore.so | VkLayer_khronos_timeline_semaphore.json | Timeline semaphore emulation |

## Usage

```bash
# Set VK_INSTANCE_LAYERS to enable layers
export VK_INSTANCE_LAYERS=VK_LAYER_KHRONOS_synchronization2,VK_LAYER_KHRONOS_shader_object
```

Or via vkCreateInstance:
```c
VkInstanceCreateInfo createInfo = {};
const char* layers[] = {"VK_LAYER_KHRONOS_synchronization2"};
createInfo.ppEnabledLayerNames = layers;
createInfo.enabledLayerCount = 1;
vkCreateInstance(&createInfo, NULL, &instance);
```