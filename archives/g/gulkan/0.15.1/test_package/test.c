/* gulkan 0.15.1 consumer test (R34/R40: exercises the real library API and
 * the system Vulkan loader path).
 *
 * Part 1 — libgulkan-0.15.so itself: gulkan_instance_new() registers and
 * instantiates the GulkanInstance GClass; get_handle() must report
 * VK_NULL_HANDLE before creation. Proves the .so loads, GType registration
 * works and the public API is callable.
 *
 * Part 2 — the loader gulkan links against: vkEnumerateInstanceExtension
 * Properties() is resolved through the same DT_NEEDED libvulkan.so that
 * libgulkan uses (OHOS system loader at /system/lib64) and answered by the
 * loader itself, without requiring a device/ICD. Proves the Vulkan linkage
 * is real, not stubbed (R40).
 */
#include "gulkan.h"

#include <vulkan/vulkan.h>

#include <stdio.h>

static int failures = 0;

#define CHECK(cond)                                                \
    do {                                                           \
        if (!(cond)) {                                             \
            printf("FAIL: %s (line %d)\n", #cond, __LINE__);       \
            ++failures;                                            \
        }                                                          \
    } while (0)

int main(void)
{
    /* Part 1: gulkan GObject API */
    GulkanInstance *instance = gulkan_instance_new();
    CHECK(instance != NULL);
    if (instance == NULL) {
        return 1;
    }
    CHECK(GULKAN_IS_INSTANCE(instance));
    CHECK(gulkan_instance_get_handle(instance) == VK_NULL_HANDLE);
    g_object_unref(instance);

    /* Part 2: loader round-trip through the linked libvulkan (no GPU needed:
     * this only queries instance extension metadata from the loader). */
    uint32_t count = 0;
    VkResult r = vkEnumerateInstanceExtensionProperties(NULL, &count, NULL);
    CHECK(r == VK_SUCCESS);
    CHECK(count > 0);

    if (failures == 0) {
        printf("PASS: gulkan real API + loader path exercised "
               "(instance new/type/handle + %u instance extensions)\n",
               count);
        return 0;
    }
    printf("FAILED: %d checks\n", failures);
    return 1;
}
