/* clfft test_package consumer probe.
 * Calls clfftGetVersion() — a real exported libclFFT symbol — to verify
 * the library links and the public header is usable. No OpenCL device
 * is required.
 */
#include <clFFT.h>
#include <stdio.h>

int main(void)
{
    cl_uint major = 0, minor = 0, patch = 0;
    cl_int err = clfftGetVersion(&major, &minor, &patch);
    if (err != CL_SUCCESS) {
        fprintf(stderr, "FAIL: clfftGetVersion error %d\n", (int)err);
        return 1;
    }
    /* Reaching here proves libclFFT linked + initialized. */
    printf("clfft OK (version %u.%u.%u)\n", major, minor, patch);
    return 0;
}
