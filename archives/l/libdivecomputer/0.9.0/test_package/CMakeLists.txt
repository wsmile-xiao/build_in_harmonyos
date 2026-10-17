cmake_minimum_required(VERSION 3.15)
project(test_libdivecomputer C)

find_package(libdivecomputer REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE libdivecomputer::libdivecomputer)

# HAVE_LIBUSB_IN_BUILD is appended to conan_toolchain.cmake by
# test_package/conanfile.py generate() from the recipe's with_libusb
# option. It reflects whether the packaged library was compiled with
# HAVE_LIBUSB (real USB/USBHID backends), and gates the transport-mask
# assertions in test_package.c.
if(HAVE_LIBUSB_IN_BUILD)
    target_compile_definitions(test_package PRIVATE HAVE_LIBUSB_IN_BUILD=1)
endif()
