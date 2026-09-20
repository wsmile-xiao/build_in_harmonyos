/* test_package/test.c — consumer-side test for libvdpau 1.5.
 *
 * Calls the wrapper's only exported symbol, vdp_device_create_x11(),
 * with a VDPAU_DRIVER value that cannot resolve to any backend. The
 * wrapper must exercise its full dlopen() dispatch chain (env lookup,
 * path construction, backend dlopen attempts, error propagation) and
 * return VDP_STATUS_NO_IMPLEMENTATION without crashing.
 */
#include <stdio.h>
#include <stdlib.h>
#include <vdpau/vdpau.h>
#include <vdpau/vdpau_x11.h>

int main(void)
{
    /* Header sanity: 1.5 still describes VDPAU interface version 1. */
    if (VDPAU_VERSION != 1) {
        fprintf(stderr, "unexpected VDPAU_VERSION %d\n", VDPAU_VERSION);
        return 1;
    }

    /*
     * Pin the driver name so the wrapper skips the DRI2 query path
     * (which would dereference the NULL Display). A plain driver name
     * without '/' is required by the wrapper, otherwise it is ignored.
     */
    if (setenv("VDPAU_DRIVER", "no_such_backend_driver", 1) != 0) {
        fprintf(stderr, "setenv failed\n");
        return 1;
    }
    unsetenv("VDPAU_DRIVER_PATH");
    unsetenv("VDPAU_TRACE");

    VdpDevice device = 0;
    VdpGetProcAddress *get_proc_address = NULL;
    VdpStatus st = vdp_device_create_x11(NULL, 0, &device, &get_proc_address);
    if (st != VDP_STATUS_NO_IMPLEMENTATION) {
        fprintf(stderr, "expected VDP_STATUS_NO_IMPLEMENTATION(%d), got %d\n",
                (int)VDP_STATUS_NO_IMPLEMENTATION, (int)st);
        return 1;
    }

    /* Error code metadata must round-trip through the header enums. */
    if (VDP_STATUS_OK != 0) {
        fprintf(stderr, "VDP_STATUS_OK must be 0\n");
        return 1;
    }

    printf("libvdpau wrapper dlopen dispatch OK: status=%d (no backend, as expected)\n",
           (int)st);
    return 0;
}
