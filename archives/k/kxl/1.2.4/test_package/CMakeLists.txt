cmake_minimum_required(VERSION 3.15)
project(test_kxl C)

# Statically link against libKXL_static.a.  The OHOS loader refuses to
# dlopen() shared libraries from /storage/... paths (namespace ACL on
# the conan cache), but it will happily exec() a binary whose libKXL.a
# is already in .text — no dlopen() required.
#
# libx11 is still linked for X11/Xlib.h and the X.Org transport chain
# that libKXL_static pulls in transitively.
find_package(libx11 REQUIRED)
find_package(kxl REQUIRED)

add_executable(test_kxl test.c)
# Use the static archive explicitly — the shared KXL target depends on
# dlopen-able libKXL.so which the OHOS loader refuses to mmap.
target_link_libraries(test_kxl PRIVATE
    kxl::kxl_static
    libx11::libx11
    dl)

enable_testing()
add_test(NAME test_kxl COMMAND test_kxl)
