#!/usr/bin/env python3
"""Conan recipe for RVVM 0.6 — the RISC-V Virtual Machine (library + CLI).

RVVM is a self-contained C11 RISC-V emulator. ``make lib all`` builds:
  - librvvm_static.a   (static library; public API in rvvmlib.h)
  - librvvm.so         (shared library)
  - rvvm               (command-line VM runner)

There are no external Conan dependencies: the core links only libc / libm and
pthread (both probed at make time by the upstream Makefile).

OHOS adaptation notes:
  - Framebuffer is disabled (USE_FB=0 / USE_SDL=0 / USE_XSHM=0): HarmonyOS PC
    has no X11 or SDL display backend in the build environment.
  - JNI binding is disabled (USE_JNI=0): it needs a JDK jni.h header that is
    not part of the OHOS build toolchain.
  - Userspace networking, PCI, FDT, RV64 and the arm64 RVJIT backend stay on.
  - Only the static library, public headers and the rvvm CLI are packaged. The
    shared library is intentionally not packaged: the upstream Makefile links
    it without a DT_SONAME (CI L5a gate) and OHOS dynamic-loader path/namespace
    handling makes static linking the safer choice for embedders.

The source URL/SHA256 are declared in conandata.yml (sources section). The SHA256
comes from FreeBSD ports distinfo (codeload tarball for tag v0.6) and is
re-verified by Conan on the first device download.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class RvvmConan(ConanFile):
    name = "rvvm"
    version = "0.6"
    description = "The RISC-V Virtual Machine (emulator with an embeddable public API)."
    license = "GPL-3.0-only OR MPL-2.0"
    homepage = "https://github.com/LekKit/RVVM"
    url = "https://github.com/LekKit/RVVM"

    # static-library: only librvvm_static.a is packaged (the upstream shared
    # library lacks DT_SONAME), so a "library" type with a shared option would
    # wrongly advertise a shared variant.
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)
        self.folders.build = "."  # RVVM's Makefile builds in-tree (BUILDDIR=build)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: obtain compiler/archiver from Conan conf, never bare shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"

        # R9: single-threaded build. The Makefile forces "-j$(JOBS)", so pass
        # JOBS=1 (not -j1, which gets overridden). BUILDDIR/BINARY make output
        # paths deterministic for package(). USE_JIT stays enabled (arm64 backend).
        self.run(
            "make lib all "
            f"CC={cc} AR={ar} "
            "BUILDDIR=build BINARY=rvvm JOBS=1 "
            "USE_FB=0 USE_SDL=0 USE_XSHM=0 USE_JNI=0 USE_TAP_LINUX=0"
        )

    def package(self):
        src = self.source_folder
        build_dir = os.path.join(self.build_folder, "build")
        inc = os.path.join(self.package_folder, "include", "rvvm")

        copy(self, "rvvmlib.h", src=os.path.join(src, "src"), dst=inc, keep_path=False)
        copy(self, "fdtlib.h", src=os.path.join(src, "src"), dst=inc, keep_path=False)
        copy(self, "*.h", src=os.path.join(src, "src", "devices"), dst=inc, keep_path=False)

        copy(self, "librvvm_static.a", src=build_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

        copy(self, "rvvm", src=build_dir,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        copy(self, "LICENSE-*", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["rvvm_static"]
        self.cpp_info.system_libs = ["pthread", "m"]
        self.cpp_info.bindirs = ["bin"]
