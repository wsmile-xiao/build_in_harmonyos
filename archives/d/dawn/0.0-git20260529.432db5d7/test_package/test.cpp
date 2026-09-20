/*
 * Dawn test_package consumer test.
 * Exercises the real Dawn native API (Null backend): create and release a
 * WGPUInstance through the exported dawn library, verifying symbols resolve
 * and the Null backend initializes on OHOS.
 */
#include <stdio.h>
#include <stdlib.h>

#include <webgpu/webgpu.h>

int main(void) {
    WGPUInstanceDescriptor descriptor = {};
    descriptor.nextInChain = NULL;

    WGPUInstance instance = wgpuCreateInstance(&descriptor);
    if (instance == NULL) {
        fprintf(stderr, "test_dawn: wgpuCreateInstance returned NULL\n");
        return 1;
    }

    wgpuInstanceRelease(instance);
    printf("test_dawn: wgpuCreateInstance/Release OK\n");
    return 0;
}
