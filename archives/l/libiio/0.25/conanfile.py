#!/usr/bin/env python3
"""Conan recipe — libiio 0.25 (CMake).

Analog Devices libiio — library + command-line tools for the Linux
Industrial I/O (IIO) subsystem.

OHOS adaptation strategy (see notes.md):
  - WITH_NETWORK_BACKEND=OFF : network backend requires HAVE_DNS_SD
    (avahi) / iiod-client; also drags in libxml2 via NEED_LIBXML2 —
    disabled to keep the recipe minimal (task strategy).
  - WITH_IIOD=OFF            : IIO daemon needs systemd/sysvinit +
    a running kernel IIO subsystem; platform infrastructure absent
    on OHOS PC.
  - WITH_USB_BACKEND=OFF     : libusb backend targets USB-connected
    ADI eval boards; libusb is not a runtime dependency we want to
    force on consumers (see notes.md for the full rationale).
  - WITH_XML_BACKEND=ON      : kept for the memory-XML context API
    (iio_create_xml_context_mem) — the only backend that works
    without kernel IIO support; requires libxml2.
  - LOCAL backend            : WITH_LOCAL_BACKEND/WITH_IIOD options
    are declared inside `IF(CMAKE_SYSTEM_NAME MATCHES "Linux")`, so
    on HarmonyOS they are never defined and the whole local-backend
    block (local.c, libini, librt, pthread) is skipped by upstream
    CMake — no patch needed. OHOS PC has no /sys/bus/iio anyway.

E120/E132: the OHOS SDK lld linker dynamically depends on
libxml2.so.16 which is not always in the loader path on workers.
We keep the default lld (GNU-ld linked ELFs are rejected by the
OHOS sandbox kernel loader — verified Permission denied) and rely
on the CI profile's LD_LIBRARY_PATH pointing at the SDK llvm/lib
directory, same approach as aeolus 0.10.4 in the main archives.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibiioConan(ConanFile):
    name = "libiio"
    version = "0.25"
    description = "Library for interfacing with Linux Industrial I/O (IIO) devices"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/analogdevicesinc/libiio"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Only the XML backend needs an external dep; network/usb/iiod are OFF.
        self.requires("libxml2/2.15.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Backend selection (task strategy — see notes.md):
        tc.variables["WITH_NETWORK_BACKEND"] = "OFF"
        tc.variables["WITH_IIOD"] = "OFF"
        tc.variables["WITH_USB_BACKEND"] = "OFF"
        tc.variables["WITH_SERIAL_BACKEND"] = "OFF"
        tc.variables["WITH_XML_BACKEND"] = "ON"
        tc.variables["WITH_ZSTD"] = "OFF"
        tc.variables["WITH_TESTS"] = "ON"     # build iio_* CLI tools (R38)
        tc.variables["WITH_EXAMPLES"] = "OFF"
        tc.variables["WITH_DOC"] = "OFF"
        tc.variables["WITH_MAN"] = "OFF"
        # WITH_TESTS=ON sets NEED_THREADS; upstream find_library(pthread)
        # fails because CMake has no Platform/HarmonyOS module so sysroot
        # library search prefixes are unknown. Pre-seed the cache variable
        # (find_library skips searching when the entry already holds a
        # value). OHOS sysroot ships a musl libpthread.a stub; pthread
        # symbols actually live in libc.
        tc.variables["PTHREAD_LIBRARIES"] = "pthread"
        # CMake's unknown-platform fallback (HarmonyOS has no
        # Platform/HarmonyOS module in this CMake) means no SONAME flag is
        # defined, so libiio.so gets stamped with NO SONAME. Downstream
        # tools then record the build-tree path (../libiio.so) in
        # DT_NEEDED and fail to load from the installed layout. Inject the
        # unversioned SONAME directly via the shared-link flags — libiio
        # is the only shared library built here.
        tc.extra_sharedlinkflags.append("-Wl,-soname,libiio.so")
        # Install path sanity for a cross-compiled consumer package.
        tc.variables["CMAKE_INSTALL_PREFIX"] = self.package_folder
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["iio"]
        # The package installs the iio_* command-line utilities into bin/
        # (WITH_TESTS=ON); declare bindirs explicitly so the R38 gate sees
        # this is a library + tools package (software-level commands.json).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libiio")
        self.cpp_info.set_property("pkg_config_name", "libiio")
