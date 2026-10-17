#!/usr/bin/env python3
"""Conan recipe for libfuse 2.9.9 — FUSE 2.x userspace filesystem library.

Build system: autotools (configure + make).
Outputs: libfuse.a (static, R26), libulockmgr.a, headers, pkg-config.

Key adaptation points (see notes.md):
  - E011: HMDFS umask 077 breaks config.status temp dirs; patched via
    configure umask 077 → 022 (patches/0001-configure-umask-022.patch).
  - --build/--host=aarch64-unknown-linux-gnu: the 2016 config.sub accepts
    the gnu triplet, so no config.guess/sub patching needed.
  - --disable-example: examples link libfuse.so and hit unimplemented
    pthread_cancel/pthread_setcancelstate (OHOS bionic, E051).
  - R26: libfuse is a system-name library → static only to avoid /lib pollution.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    rmdir,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfuseConan(ConanFile):
    name = "libfuse"
    version = "2.9.9"
    description = "FUSE 2.x — Filesystem in Userspace library"
    license = "LGPL-2.1 AND GPL-2.0"
    homepage = "https://github.com/libfuse/libfuse"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # R32: settings.os judgment must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libfuse is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")
        # R26: libfuse is a system-name library — shared would pollute /lib
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libfuse is a system-name library; shared option disabled (R26)"
            )

    def requirements(self):
        pass  # no external conan dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name library — static only
        tc.configure_args.extend([
            "--enable-static",
            "--disable-shared",
            "--disable-example",
            "--enable-util",
        ])
        if str(self.settings.os) == "OHOS":
            # config.sub (even 2023) maps -ohos fine for config.guess,
            # but libtool's old ltmain.sh handles -gnu more stably. Use
            # the gnu triplet so autotools cross-detection works.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # remove libtool .la wrappers and pkg-config (conan manages deps)
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["fuse", "ulockmgr"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.includedirs = ["include", "include/fuse"]
        # fuse_common.h enforces _FILE_OFFSET_BITS=64 via #error
        self.cpp_info.defines = ["_FILE_OFFSET_BITS=64"]
