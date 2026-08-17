#include <vulkan/vulkan.h>
#include <stdio.h>

int main(void) {
    /* Call a loader-exported function that doesn't require a valid instance */
    PFN_vkGetInstanceProcAddr getProcAddr = vkGetInstanceProcAddr;
    if (getProcAddr == NULL) {
        printf("FAIL: vkGetInstanceProcAddr is NULL\n");
        return 1;
    }

    /* vkCreateInstance is a global function that should always be resolvable */
    PFN_vkVoidFunction func = vkGetInstanceProcAddr(NULL, "vkCreateInstance");
    if (func != NULL) {
        printf("PASS: vkGetInstanceProcAddr resolved vkCreateInstance\n");
        return 0;
    }
    printf("FAIL: vkGetInstanceProcAddr returned NULL for vkCreateInstance\n");
    return 1;
}
