#!/usr/bin/env python3
"""Conan recipe — libusbsio 2.1.13 (NXP LIBUSBSIO USB-HID serial I/O library).

LIBUSBSIO is NXP's host-side library for communicating over USB-HID with
LPC-Link2 / MCU-Link debug probes (I2C / SPI / GPIO bridge). Pure C, two
translation units (src/lpcusbsio.c + src/hid_api/linux/hid.c — an embedded
hidapi 0.11.2-era hidraw backend).

Source-of-record note (see notes.md for the full equivalence evidence):
the task's designated upstream https://github.com/Intronics/libusbsio
(tag v2.1.13) has been deleted from GitHub (404; the account still exists
with zero public repos). NXP's official download page only offers Rev
2.2.1 behind an account login. The source URL in conandata.yml points to
a byte-stable public GitHub snapshot (monwarez/libusbsio @ 8577280) of
the same NXP LIBUSBSIO v2.1c codebase — proven equivalent to the 2.1.13
Linux artefacts via MD5 of the prebuilt .so files shipped in the official
PyPI libusbsio 2.1.13 wheel (identical to 2.1.11's, i.e. the C library
was never changed for Linux across 2.1.10-2.1.13; only the Windows DLL
moved to v2.1e).

OHOS adaptation:
  - Linux hidraw backend kept (OHOS sysroot ships linux/hidraw.h and the
    hidraw ioctls); open/read/write paths are plain ioctl() and need no
    udev.
  - Device enumeration uses libudev: OHOS has no systemd libudev, so the
    recipe requires libudev-zero/1.0.4 (drop-in static libudev from this
    repo's registry).
  - No CMake upstream: the two C files are compiled directly from the
    recipe (equivalent to upstream `make` for the Linux target), with
    compiler/flags taken from the Conan toolchain (R33).
  - R26: libusbsio is NOT a system-name library on OHOS; default shared
    build with the dependency chain managed by Conan.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibusbsioConan(ConanFile):
    name = "libusbsio"
    version = "2.1.13"
    description = "NXP LIBUSBSIO - USB serial I/O library for LPC-Link2 / MCU-Link bridges (I2C/SPI/GPIO over USB-HID)"
    license = "BSD-3-Clause"
    homepage = "https://www.nxp.com/design/design-center/software/development-software/libusbsio-host-library-for-usb-enabled-mcus:LIBUSBSIO"
    url = "https://github.com/monwarez/libusbsio"
    topics = ("usb", "hid", "i2c", "spi", "gpio", "nxp", "embedded")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        # No patches needed for this version (see notes.md); the hook call
        # is kept so conandata patches would be exported automatically if
        # any are added later.
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC
        # The recipe only implements the Linux/hidraw backend.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libusbsio 2.1.13 recipe implements the Linux hidraw backend only, got os={self.settings.os}"
            )

    def requirements(self):
        # Enumeration backend: drop-in static libudev replacement (the
        # upstream makefile uses `pkg-config libudev` on Linux; OHOS has
        # no systemd libudev, so the libudev-zero package from this
        # registry provides the API surface the embedded hid.c uses).
        self.requires("libudev-zero/1.0.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"], sha256=source_data["sha256"], strip_root=True)

    def generate(self):
        # Nothing to generate: the build() step compiles the two C files
        # directly with the compiler from the Conan profile conf (R33 —
        # never from shell env vars).
        pass

    def build(self):
        apply_conandata_patches(self)

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables['c'] not set in the profile; "
                "cannot build libusbsio (R33)"
            )

        src = self.source_folder
        inc = [
            os.path.join(src, "include"),
            os.path.join(src, "src", "hid_api", "hidapi"),
        ]
        # libudev-zero headers come through the dependency package
        # (self.dependencies.items() yields (require, conanfile) tuples)
        for req, dep in self.dependencies.items():
            if req.ref.name == "libudev-zero":
                inc.extend(dep.cpp_info.includedirs)

        cflags = [
            "-O2" if self.settings.build_type == "Release" else "-O0 -g",
            "-Wall",
            "-DNDEBUG" if self.settings.build_type == "Release" else "",
        ]
        if self.options.shared or self.options.get_safe("fPIC"):
            cflags.insert(0, "-fPIC")

        objs = []
        for cfile in (
            os.path.join("src", "lpcusbsio.c"),
            os.path.join("src", "hid_api", "linux", "hid.c"),
        ):
            obj = os.path.join(self.build_folder, os.path.basename(cfile) + ".o")
            self.run(
                f'"{cc}" -c "{os.path.join(src, cfile)}" '
                f'{" ".join(f"-I{i}" for i in inc)} '
                f'{" ".join(f for f in cflags if f)} '
                f'-o "{obj}"',
                cwd=self.build_folder,
            )
            objs.append(obj)

        udev_lib = None
        for req, dep in self.dependencies.items():
            if req.ref.name == "libudev-zero":
                for l in dep.cpp_info.libs:
                    udev_lib = os.path.join(dep.cpp_info.libdirs[0], f"lib{l}.a")
        if not udev_lib:
            raise ConanInvalidConfiguration("libudev-zero static lib not found")

        obj_list = " ".join('"%s"' % o for o in objs)
        if self.options.shared:
            lib_out = os.path.join(self.build_folder, "libusbsio.so")
            # -Wl,-soname keeps L5 happy (DT_SONAME on the shared object)
            self.run(
                f'"{cc}" -shared -Wl,-soname,libusbsio.so '
                f'-o "{lib_out}" {obj_list} "{udev_lib}"',
                cwd=self.build_folder,
            )
        else:
            lib_out = os.path.join(self.build_folder, "libusbsio.a")
            ar = compiler_executables.get("ar") or "llvm-ar"
            self.run(
                f'"{ar}" rcs "{lib_out}" {obj_list}',
                cwd=self.build_folder,
            )

    def package(self):
        for ext in (".so", ".a"):
            lib = os.path.join(self.build_folder, f"libusbsio{ext}")
            if os.path.isfile(lib):
                copy(self, f"libusbsio{ext}", self.build_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "lpcusbsio.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "lpcusbsio_protocol.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "BSD-3-clause.txt", os.path.join(self.source_folder, "license"),
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["usbsio"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libusbsio")
        self.cpp_info.set_property("cmake_target_name", "libusbsio::libusbsio")
        # The libudev-zero dependency is propagated so consumers that
        # enumerate devices resolve udev symbols.
        self.cpp_info.requires = ["libudev-zero::libudev-zero"]
