#include <va/va.h>
#include <va/va_drm.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>

int main(void) {
    /* Try to open a real DRM device for meaningful VA-API initialization test */
    int drm_fd = open("/dev/dri/card0", O_RDWR);
    if (drm_fd < 0) {
        /* No DRM device available - verify library symbols are linkable */
        VADisplay display = NULL;
        int major = 0, minor = 0;
        VAStatus status = vaInitialize(display, &major, &minor);
        /* Expect a non-success error code (VA_STATUS_ERROR_INVALID_DISPLAY)
         * when passing a NULL display - verifies the API symbol is callable
         * and the argument validation path works */
        if (status != VA_STATUS_SUCCESS) {
            printf("VA-API library linked successfully (no DRM device for full test)\n");
            return 0;
        }
        fprintf(stderr, "Unexpected vaInitialize return: %d\n", status);
        return 1;
    }

    /* Real DRM device available - test actual VA-API initialization */
    VADisplay display = vaGetDisplayDRM(drm_fd);
    if (display == NULL) {
        fprintf(stderr, "vaGetDisplayDRM failed\n");
        close(drm_fd);
        return 1;
    }

    int major = 0, minor = 0;
    VAStatus status = vaInitialize(display, &major, &minor);
    if (status != VA_STATUS_SUCCESS) {
        fprintf(stderr, "vaInitialize failed: %d\n", status);
        vaTerminate(display);
        close(drm_fd);
        return 1;
    }

    printf("VA-API initialized: version %d.%d\n", major, minor);
    vaTerminate(display);
    close(drm_fd);
    return 0;
}
