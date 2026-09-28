cmake_minimum_required(VERSION 3.15)
project(test_iio_sensor C)

add_executable(test_iio_sensor test.c)

# IIO_SENSOR_PROXY_PATH / MONITOR_SENSOR_PATH are injected by
# test_package/conanfile.py build() so test.c stats the Conan-packaged
# binaries, not a host PATH lookup (R34).
if(NOT DEFINED IIO_SENSOR_PROXY_PATH)
    message(FATAL_ERROR "IIO_SENSOR_PROXY_PATH must be defined (Conan packaged iio-sensor-proxy path)")
endif()
if(NOT DEFINED MONITOR_SENSOR_PATH)
    message(FATAL_ERROR "MONITOR_SENSOR_PATH must be defined (Conan packaged monitor-sensor path)")
endif()
target_compile_definitions(test_iio_sensor PRIVATE
    IIO_SENSOR_PROXY_PATH="${IIO_SENSOR_PROXY_PATH}"
    MONITOR_SENSOR_PATH="${MONITOR_SENSOR_PATH}")

# No add_test(): test_iio_sensor is cross-compiled for OHOS aarch64 and
# cannot be executed on the x86 CI worker (Exec format error). It is a
# compile-time verification target; runtime ELF checks live in conanfile.py.