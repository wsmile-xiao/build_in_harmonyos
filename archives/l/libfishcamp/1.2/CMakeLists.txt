# Build script for libfishcamp (HarmonyOS adaptation).
#
# Upstream ships a CMakeLists.txt that requires the full INDI framework
# (find_package(INDI), CMakeCommon from the parent monorepo, firmware/udev
# installs). This recipe replaces it with a minimal, self-contained build that
# only compiles fishcamp.c and links libusb-1.0 — which is all the library
# actually needs.

cmake_minimum_required(VERSION 3.16)
project(fishcamp C)

# libusb-1.0 is provided by Conan's CMakeDeps. The generated config file is
# libusb-1.0Config.cmake and the imported target is libusb-1.0::libusb-1.0
# (NOT libusb/libusb::libusb), so we must match that exact name.
find_package(libusb-1.0 CONFIG REQUIRED)

add_library(fishcamp fishcamp.c)
set_target_properties(fishcamp PROPERTIES
    VERSION 1.2
    SOVERSION 1
    C_STANDARD 99
    C_STANDARD_REQUIRED ON)

# PUBLIC: fishcamp's public headers (fishcamp_common.h) include <libusb.h>, so
# consumers must also see libusb's include path and link it transitively.
target_link_libraries(fishcamp PUBLIC libusb-1.0::libusb-1.0)

# fishcamp.h includes its sibling fishcamp_common.h via a quoted include, so the
# source directory must be on the include path for both the build and consumers.
target_include_directories(fishcamp PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>)

include(GNUInstallDirs)
install(FILES fishcamp.h fishcamp_common.h DESTINATION include)
install(TARGETS fishcamp
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
