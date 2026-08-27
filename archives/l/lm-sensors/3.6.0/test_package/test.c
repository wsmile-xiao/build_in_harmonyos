#include <stdio.h>
#include <sensors/sensors.h>

int main(void) {
    /* Verify libsensors is linked and API version is accessible */
    printf("libsensors version: %s\n", libsensors_version);
    printf("API version: 0x%x\n", SENSORS_API_VERSION);

    /* Initialize libsensors (NULL = use default config path).
     * On systems without /sys/class/hwmon this returns non-zero,
     * but the function itself must be callable. */
    int ret = sensors_init(NULL);
    if (ret != 0) {
        printf("sensors_init returned %d (expected without hwmon)\n", ret);
    } else {
        /* Iterate detected chips (will be empty on systems without sensors) */
        int nr = 0;
        const sensors_chip_name *chip;
        while ((chip = sensors_get_detected_chips(NULL, &nr))) {
            printf("Detected chip: %s\n", chip->prefix ? chip->prefix : "(unknown)");
        }
    }

    /* Cleanup is always safe to call */
    sensors_cleanup();

    printf("Test passed: libsensors API is functional\n");
    return 0;
}
