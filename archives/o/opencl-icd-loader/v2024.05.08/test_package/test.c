#include <CL/cl.h>
#include <stdio.h>

int main(void) {
    cl_uint num_platforms = 0;
    cl_int err = clGetPlatformIDs(0, NULL, &num_platforms);
    /* CL_SUCCESS (0) means platforms were found.
     * -1001 (CL_PLATFORM_NOT_FOUND_KHR) means no OpenCL drivers installed,
     *   which is expected on build machines without OpenCL hardware.
     * Either way, the library loaded and the API was callable = OK. */
    if (err == CL_SUCCESS || err == -1001) {
        printf("OpenCL ICD Loader test: clGetPlatformIDs returned %d, %u platform(s)\n",
               err, num_platforms);
        printf("test opencl-icd-loader: OK\n");
        return 0;
    } else {
        printf("OpenCL ICD Loader test: clGetPlatformIDs failed (err=%d)\n", err);
        return 1;
    }
}
