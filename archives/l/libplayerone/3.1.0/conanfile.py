#!/usr/bin/env python3
"""libplayerone 3.1.0 — Player One Astronomy camera SDK (installed prebuilt package).

The upstream "library" is not compiled from source: it ships vendor-prebuilt
per-architecture shared objects (libPlayerOneCamera.bin) plus a single
self-contained public header (PlayerOneCamera.h) and a udev rule. The upstream
CMakeLists only IMPORTs the .bin and installs it (CMake target PlayerOneCamera,
VERSION 3.1.0 / SOVERSION 3, via install_imported). We install the same
artifacts the way CMake's install_imported would:

  lib/libPlayerOneCamera.so.3   <- copy of armv8/libPlayerOneCamera.bin
                                   (renamed to match the vendor SONAME
                                    libPlayerOneCamera.so.3)
  lib/libPlayerOneCamera.so     -> symlink to the above (so -lPlayerOneCamera
                                   resolves at link time)
  include/libplayerone/PlayerOneCamera.h
  lib/udev/rules.d/99-player_one_astronomy.rules
  licenses/license.txt

Only the armv8/aarch64 vendor binary is packaged (the OHOS target arch). The
vendor .so carries NEEDED libusb-1.0.so.0, so libusb is declared as a
run-only dependency (it is not needed to produce the package).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy


class LibPlayerOneConan(ConanFile):
    name = "libplayerone"
    version = "3.1.0"
    description = ("Player One Astronomy camera SDK: prebuilt vendor shared "
                   "library and public header for POA/ONE/ZWO astronomy "
                   "cameras over USB")
    license = "MIT"
    url = "https://salsa.debian.org/debian-astro-team/libplayerone"
    homepage = "https://libplayerone.org/"
    topics = ("astronomy", "camera", "usb", "sdk", "prebuilt")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        # The vendor .so has NEEDED libusb-1.0.so.0; only required at run time.
        self.requires("libusb/1.0.27", run=True)

    def validate(self):
        if not self.options.shared:
            raise ConanException(
                "libplayerone ships only a vendor-prebuilt shared object; "
                "shared=False is not supported")
        if str(self.settings.arch) != "armv8":
            raise ConanException(
                "libplayerone vendor binaries are aarch64/armv8 only; "
                f"got arch={self.settings.arch}")

    def package_id(self):
        # Prebuilt vendor binary: the build toolchain / build type do not affect it.
        del self.info.settings.compiler
        del self.info.settings.build_type

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        src_armv8 = os.path.join(self.source_folder, "armv8")
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)

        # Vendor shared object, renamed to match its own SONAME
        # (libPlayerOneCamera.so.3) so the runtime loader finds it.
        copy(self, "libPlayerOneCamera.bin", src_armv8, libdir)
        so3 = os.path.join(libdir, "libPlayerOneCamera.so.3")
        os.rename(os.path.join(libdir, "libPlayerOneCamera.bin"), so3)
        os.chmod(so3, 0o755)
        # -lPlayerOneCamera resolves through this symlink at link time.
        os.symlink("libPlayerOneCamera.so.3",
                   os.path.join(libdir, "libPlayerOneCamera.so"))

        # Public header (the upstream CMake installs it under include/libplayerone).
        copy(self, "PlayerOneCamera.h", self.source_folder,
             os.path.join(self.package_folder, "include", "libplayerone"))

        # udev rule for the camera's USB device.
        udev = os.path.join(self.package_folder, "lib", "udev", "rules.d")
        os.makedirs(udev, exist_ok=True)
        copy(self, "99-player_one_astronomy.rules", self.source_folder, udev)

        # License.
        copy(self, "license.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libplayerone")
        self.cpp_info.set_property("cmake_target_name", "libplayerone::PlayerOneCamera")
        self.cpp_info.set_property("pkg_config_name", "libplayerone")
        self.cpp_info.libs = ["PlayerOneCamera"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include/libplayerone"]
