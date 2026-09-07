#include <CL/cl.h>
#include <stdio.h>

int main(void) {
    cl_uint num_platforms = 0;
    cl_int err = clGetPlatformIDs(0, NULL, &num_platforms);
    /* CL_SUCCESS (0) means platforms were found.
     * -1001 (CL_PLATFORM_NOT_FOUND_KHR) means no OpenCL driver is
     * installed, which is expected on build workers without OpenCL
     * hardware. Either way the loader library loaded and the entry
     * point was callable, so the test passes. */
    if (err == CL_SUCCESS || err == -1001) {
        printf("ocl-icd test: clGetPlatformIDs returned %d, %u platform(s)\n",
               err, (unsigned)num_platforms);
        printf("test ocl-icd: OK\n");
        return 0;
    }
    printf("ocl-icd test: clGetPlatformIDs failed (err=%d)\n", err);
    return 1;
}
