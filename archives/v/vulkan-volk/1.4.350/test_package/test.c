/* test.c — consumer test for vulkan-volk 1.4.350
 *
 * This test exercises volk's public API:
 *   - volkInitialize(): loads the Vulkan loader dynamically
 *   - volkGetInstanceVersion(): returns the Vulkan instance version
 *
 * On headless systems without a Vulkan loader, volkInitialize() returns
 * VK_ERROR_INITIALIZATION_FAILED, which is expected and not a failure.
 * The test verifies that the library links and the API symbols resolve.
 */
#include <volk.h>
#include <stdio.h>

int main(void) {
    /* volkInitialize() loads the Vulkan loader via dlopen.
     * On systems without Vulkan, it returns VK_ERROR_INITIALIZATION_FAILED.
     * The test succeeds as long as the API is callable (links correctly). */
    VkResult result = volkInitialize();
    if (result == VK_SUCCESS) {
        uint32_t version = volkGetInstanceVersion();
        printf("volk: Vulkan instance version: %u.%u.%u\n",
               VK_API_VERSION_MAJOR(version),
               VK_API_VERSION_MINOR(version),
               VK_API_VERSION_PATCH(version));
    } else {
        printf("volk: volkInitialize() returned %d (expected on headless)\n", result);
    }
    return 0;
}
