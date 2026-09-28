#include <stdio.h>
#include <sys/stat.h>

/* IIO_SENSOR_PROXY_PATH / MONITOR_SENSOR_PATH are baked in at compile time
   by test_package/conanfile.py (cmake.configure variables) and point at the
   Conan-packaged binaries, NOT a host PATH lookup (R34: test must target
   the packaged binaries).  test_iio_sensor is a compile-time verification
   target: it cannot be executed on the x86 CI worker because it is
   cross-compiled for OHOS aarch64 (Exec format error). */
#ifndef IIO_SENSOR_PROXY_PATH
#error "IIO_SENSOR_PROXY_PATH must be defined (Conan packaged iio-sensor-proxy absolute path)"
#endif
#ifndef MONITOR_SENSOR_PATH
#error "MONITOR_SENSOR_PATH must be defined (Conan packaged monitor-sensor absolute path)"
#endif

int main(void) {
    struct stat st;
    if (stat(IIO_SENSOR_PROXY_PATH, &st) != 0) {
        fprintf(stderr, "packaged iio-sensor-proxy not found at %s\n", IIO_SENSOR_PROXY_PATH);
        return 1;
    }
    printf("packaged iio-sensor-proxy present at %s\n", IIO_SENSOR_PROXY_PATH);
    if (stat(MONITOR_SENSOR_PATH, &st) != 0) {
        fprintf(stderr, "packaged monitor-sensor not found at %s\n", MONITOR_SENSOR_PATH);
        return 1;
    }
    printf("packaged monitor-sensor present at %s\n", MONITOR_SENSOR_PATH);
    return 0;
}