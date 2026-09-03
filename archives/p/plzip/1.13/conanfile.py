#!/usr/bin/env python3
"""Conan recipe for plzip — Parallel implementation of the lzip compressor."""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PlzipConan(ConanFile):
    name = "plzip"
    version = "1.13"
    description = "Massively parallel implementation of the lzip data compressor"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/lzip/plzip.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("plzip is supported only on Linux/OHOS")

    def requirements(self):
        self.requires("lzlib/1.15")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E095: plzip's custom configure (not autoconf) doesn't read $CXX env var.
        # R33: get compiler from Conan conf, not shell env.
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cxx = compilers.get("cpp", "clang++")
        tc.configure_args.append(f"CXX={cxx}")
        # plzip's configure clears CPPFLAGS/LDFLAGS env vars set by Conan,
        # so pass lzlib include/lib paths as configure args.
        lzlib = self.dependencies["lzlib"]
        inc_flags = " ".join(f"-I{d}" for d in lzlib.cpp_info.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in lzlib.cpp_info.libdirs)
        if inc_flags:
            tc.configure_args.append(f"CPPFLAGS={inc_flags}")
        if lib_flags:
            tc.configure_args.append(f"LDFLAGS={lib_flags}")
        tc.generate()

        # E106: lld linker depends on libxml2.so.16 in the LLVM lib directory.
        # CI workers may not have this in LD_LIBRARY_PATH by default.
        env = Environment()
        for lib_dir in glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"):
            if os.path.isfile(os.path.join(lib_dir, "libxml2.so.16")):
                env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                break
        env.vars(self).save_script("lld_fix")

    def build(self):
        apply_conandata_patches(self)
        # E165: Fix shebang for HarmonyOS (/bin/sh -> /system/bin/sh)
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path, "#!/bin/sh", "#!/system/bin/sh", strict=False)
        replace_in_file(self, configure_path, "#! /bin/sh", "#! /system/bin/sh", strict=False)
        # Also fix SHELL in Makefile.in
        makefile_in_path = os.path.join(self.source_folder, "Makefile.in")
        replace_in_file(self, makefile_in_path, "SHELL = /bin/sh", "SHELL = /system/bin/sh", strict=False)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Run upstream tests (CI L1 requires make check in build)
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
