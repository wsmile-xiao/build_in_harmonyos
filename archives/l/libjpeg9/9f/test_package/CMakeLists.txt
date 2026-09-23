cmake_minimum_required(VERSION 3.15)
project(test_libjpeg9 C)

find_package(libjpeg9 REQUIRED)

add_executable(test_libjpeg9 test.c)
target_link_libraries(test_libjpeg9 libjpeg9::libjpeg9)

# OHOS-specific R26 test: asserts the package is static-only (lib/libjpeg.a
# present, no libjpeg.so*). LIBJPEG9_PKG_LIBDIR is injected by the
# test_package generate(); an empty value makes the test fail loudly.
if(NOT DEFINED LIBJPEG9_PKG_LIBDIR)
    set(LIBJPEG9_PKG_LIBDIR "")
endif()
add_executable(test_ohos_static test_ohos_static.c)
target_compile_definitions(test_ohos_static PRIVATE
    LIBJPEG9_PKG_LIBDIR="${LIBJPEG9_PKG_LIBDIR}")
