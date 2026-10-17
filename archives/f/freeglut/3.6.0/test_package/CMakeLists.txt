cmake_minimum_required(VERSION 3.15)
project(test_freeglut C)

find_package(freeglut CONFIG REQUIRED)

add_executable(test_freeglut test_freeglut.c)
target_link_libraries(test_freeglut PRIVATE freeglut::freeglut)

# The GLES2/EGL headers come from the OHOS sysroot; the toolchain already adds
# it to the search path, and freeglut's package_info contributes the FREEGLUT_GLES
# define (needed to bootstrap GLES header inclusion in freeglut_std.h).
