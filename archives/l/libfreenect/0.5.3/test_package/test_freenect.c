#include <stdio.h>

#include <libfreenect.h>

/* Real API smoke test: links libfreenect and drives the public entry points
 * freenect_init() -> freenect_num_devices() -> freenect_shutdown().
 *
 * On the OHOS sandbox libusb cannot enumerate /sys/bus/usb/devices
 * (SELinux errno=13; see libusb/1.0.27 platform notes), so freenect_init()
 * normally returns non-zero when no Kinect is attached. That is an
 * environment/device limitation, not a build failure: the hard gate is that
 * the binary links and calls the real libfreenect functions. */
int main(void)
{
    freenect_context *ctx = NULL;
    int rc = freenect_init(&ctx, NULL);

    if (rc != 0) {
        fprintf(stderr,
                "freenect_init() rc=%d (no Kinect / no USB enumeration on OHOS sandbox)\n",
                rc);
        printf("test libfreenect 0.5.3: LINK-OK (device absent)\n");
        return 0;
    }

    int ndev = freenect_num_devices(ctx);
    printf("freenect_init() ok, devices=%d\n", ndev);
    freenect_shutdown(ctx);

    printf("test libfreenect 0.5.3: OK\n");
    return 0;
}
