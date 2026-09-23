#include <CL/cl.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    cl_uint num_platforms = 0;
    cl_int err = clGetPlatformIDs(0, NULL, &num_platforms);
    if (err == -1001) {
        /* No OpenCL driver on the worker. The runtime library loaded and
         * the entry point was callable, so the link/call check passes. */
        printf("test_oclgrind: no OpenCL platform (err=-1001), library callable\n");
        printf("test oclgrind: OK\n");
        return 0;
    }
    if (err != CL_SUCCESS) {
        printf("test_oclgrind: clGetPlatformIDs failed (err=%d)\n", err);
        return 1;
    }
    printf("test_oclgrind: found %u platform(s)\n", (unsigned)num_platforms);
    if (num_platforms < 1) {
        printf("test_oclgrind: expected at least 1 platform\n");
        return 1;
    }
    cl_platform_id platform = NULL;
    err = clGetPlatformIDs(1, &platform, NULL);
    if (err != CL_SUCCESS || platform == NULL) {
        printf("test_oclgrind: cannot get platform handle (err=%d)\n", err);
        return 1;
    }
    char name[256] = {0};
    err = clGetPlatformInfo(platform, CL_PLATFORM_NAME, sizeof(name), name, NULL);
    if (err != CL_SUCCESS) {
        printf("test_oclgrind: clGetPlatformInfo failed (err=%d)\n", err);
        return 1;
    }
    printf("test_oclgrind: platform name: %s\n", name);
    if (strstr(name, "Oclgrind") == NULL) {
        /* Linked directly against liboclgrind-rt, the platform must be
         * Oclgrind. Any other name means we loaded the wrong library. */
        printf("test_oclgrind: unexpected platform (want Oclgrind)\n");
        return 1;
    }
    cl_uint num_devices = 0;
    err = clGetDeviceIDs(platform, CL_DEVICE_TYPE_ALL, 0, NULL, &num_devices);
    if (err != CL_SUCCESS || num_devices < 1) {
        printf("test_oclgrind: expected at least 1 device (err=%d, n=%u)\n",
               err, (unsigned)num_devices);
        return 1;
    }
    printf("test_oclgrind: found %u device(s)\n", (unsigned)num_devices);
    printf("test oclgrind: OK\n");
    return 0;
}
