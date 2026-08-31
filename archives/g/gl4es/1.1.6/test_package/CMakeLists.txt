cmake_minimum_required(VERSION 3.15)
project(test_gl4es C)

find_package(gl4es REQUIRED)

# gl4es::gl4es provides the desktop libGL (-lGL); the offscreen render test ALSO
# needs the system EGL to create a GLES2 pbuffer context.
#
# find_library(EGL) does NOT find it by default in the conan OHOS toolchain:
# CMAKE_SYSTEM_NAME is reported as "HarmonyOS" (unknown to CMake), so the sysroot
# triplet lib dir <sysroot>/usr/lib/aarch64-linux-ohos is not on the default
# search path. Search it explicitly, plus /system/lib64 (the native OHOS EGL).
find_library(EGL_LIBRARY EGL
    PATHS
        "${CMAKE_SYSROOT}/usr/lib"
        "${CMAKE_SYSROOT}/usr/lib/aarch64-linux-ohos"
        "${CMAKE_SYSROOT}/usr/lib/aarch64-linux-gnu"
        "/system/lib64"
        "/system/lib"
    NO_DEFAULT_PATH)
if(NOT EGL_LIBRARY)
    message(FATAL_ERROR "EGL not found (CMAKE_SYSROOT=${CMAKE_SYSROOT}): the offscreen render test needs libEGL")
endif()

add_executable(test_gl4es test.c)
target_link_libraries(test_gl4es PRIVATE gl4es::gl4es ${EGL_LIBRARY})
# gl4es ships an EGL/egl.h that pulls X11 unless EGL_NO_X11 is set (gl4es is built NOX11).
target_compile_definitions(test_gl4es PRIVATE EGL_NO_X11)
