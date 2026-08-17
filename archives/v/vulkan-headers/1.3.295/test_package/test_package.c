#include <vulkan/vulkan_core.h>
#include <stdio.h>

int main(void) {
    printf("VK_HEADER_VERSION = %d\n", VK_HEADER_VERSION);
    printf("VK_HEADER_VERSION_COMPLETE = %u\n", (unsigned)VK_HEADER_VERSION_COMPLETE);
    if (VK_HEADER_VERSION > 0) {
        printf("PASS: Vulkan headers found and version is valid\n");
        return 0;
    }
    printf("FAIL: VK_HEADER_VERSION is zero or negative\n");
    return 1;
}
