#!/usr/bin/env python3
"""Conan recipe for binn 3.0 — Binn is a serialization library for C.

binn upstream uses a plain Makefile (no configure script):
  - `make all`        → libbinn.so.3.0 (+ libbinn.so.3 / libbinn.so symlinks)
  - `make static`     → libbinn.a
  - `make test`       → builds test/test_binn from test/test_binn.c +
                        test/test_binn2.c and runs the upstream regression suite
  - `make install`    → installs the .so + src/binh.h under PREFIX

Build notes:
  - R33: CC/CFLAGS/LDFLAGS come from the Conan toolchain (AutotoolsToolchain
    generates conanbuild env); the Makefile uses `CC ?=` / `CFLAGS +=`, so
    toolchain-provided values are honored without relying on shell vars.
  - R32: settings.os must check in ("Linux", "OHOS"), not == "Linux".
  - E074: HarmonyOS SELinux forbids jobserver FIFO → all make with -j1.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class BinnConan(ConanFile):
    name = "binn"
    version = "3.0"
    description = "Binn - a binary serialization library for C (fast, compact, easy to use)"
    license = "MIT"
    homepage = "https://github.com/liteserver/binn"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: platform gate must accept both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "binn is supported only on Linux/OHOS, not " + str(self.settings.os))

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R33: compilers/flags come from the toolchain, never bare shell vars
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # binn Makefile: all → shared .so; static → libbinn.a
        target = "all" if self.options.shared else "static"
        self.run(f"make -j1 {target}", cwd=self.source_folder, env="conanbuild")
        # L1: upstream regression suite (test_binn = test_binn.c + test_binn2.c)
        self.run("make -j1 test", cwd=self.source_folder, env="conanbuild")

    def package(self):
        import os
        from conan.tools.files import copy
        if self.options.shared:
            # make install installs the .so + symlinks + src/binn.h
            self.run(f"make install PREFIX={self.package_folder}",
                     cwd=self.source_folder, env="conanbuild")
        else:
            # static: upstream `make install` only installs the shared
            # LIBRARY; copy libbinn.a and binn.h manually (R26 static path)
            copy(self, "libbinn.a", self.source_folder,
                 os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "src/binn.h", self.source_folder,
                 os.path.join(self.package_folder, "include"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["binn"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
