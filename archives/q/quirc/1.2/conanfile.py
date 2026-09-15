#!/usr/bin/env python3
"""Conan recipe — quirc 1.2 (raw Makefile project, no configure script).

quirc is a small QR-code recognition library (decoder only), pure C99,
zero external dependencies for the library itself (lib/ links only -lm).
The upstream Makefile also builds SDL/OpenCV demo tools and a jpeg/png
test tool; none of those are library dependencies and none are packaged.

Build notes (verified on OHOS aarch64 device):
- Upstream Makefile injects `pkg-config --cflags sdl` stderr text into
  CFLAGS when SDL is absent; the pkg-config variables are overridden on
  the make command line (empty) instead of patching the Makefile.
- R33: compiler/ar/ranlib come from Conan conf, never shell env vars.
- R9: make runs with -j1.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class QuircConan(ConanFile):
    name = "quirc"
    version = "1.2"
    description = "QR-code recognition library (decoder only, pure C)"
    license = "ISC"
    homepage = "https://github.com/dlbeer/quirc"
    url = "https://github.com/dlbeer/quirc"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # quirc has no external dependencies

    def layout(self):
        basic_layout(self)
        # Build in the source root: the upstream Makefile lives there and
        # expects to run in-tree (this conan's basic_layout otherwise puts
        # the build in a "build-release" subfolder with no Makefile).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: toolchain executables from Conan conf (profile-provided)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"

        cflags = "-O2" if self.settings.build_type == "Release" else "-O0 -g"
        cflags += " -fPIC"

        # Override pkg-config-derived SDL/OpenCV variables: absent on the
        # build host, the upstream Makefile would otherwise splice the
        # pkg-config error text into the compile command line.
        targets = "libquirc.a"
        if self.options.shared:
            targets += " libquirc.so.1.2"
        self.run(
            f"make {targets} -j1"
            f" CC={cc} AR={ar} RANLIB={ranlib}"
            f" SDL_CFLAGS= SDL_LIBS= OPENCV_CFLAGS= OPENCV_LIBS="
            f" CFLAGS=\"{cflags}\" LDFLAGS=\"\""
        )

    def package(self):
        copy(self, "quirc.h", os.path.join(self.source_folder, "lib"),
             os.path.join(self.package_folder, "include"))
        copy(self, "*.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            # Copy (not symlink: HMDFS-safe) the versioned .so also as
            # libquirc.so so consumer linking with -lquirc resolves; the
            # runtime object remains libquirc.so.1.2 (its embedded SONAME).
            copy(self, "libquirc.so.1.2", self.source_folder,
                 os.path.join(self.package_folder, "lib"))
            src = os.path.join(self.package_folder, "lib", "libquirc.so.1.2")
            dst = os.path.join(self.package_folder, "lib", "libquirc.so")
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["quirc"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
