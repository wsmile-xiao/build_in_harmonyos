#!/usr/bin/env python3
"""Conan recipe for srs-state 1.9.5 — SRS fork of the State Threads library (libst).

srs-state-threads is a coroutine-based user-space threading library forked from
SGI/Netscape's State Threads and patched for SRS (Simple Realtime Server).
It produces libst.a / libst.so.1.9 plus the st.h header.

Build system: plain Makefile (no configure script).  Upstream targets:
  - linux-optimized / linux-debug  (library, BUILD=OPT/DBG)
  - linux-debug-utest              (library + bundled gtest unit tests)

OHOS adaptation notes (verified on aarch64 HarmonyOS PC, clang 15):
  - TARGETDIR must be overridden: Makefile derives it from `uname -r`, which
    on OHOS returns a string containing spaces ("HongMeng Kernel 1.12.0"),
    breaking the $(TARGETDIR)/%.o pattern rules.
  - LDFLAGS must be overridden: upstream passes bare `-soname=...` which the
    clang driver rejects; use `-Wl,-soname,libst.so.1`.
  - aarch64 context-switch assembly lives in md_linux2.S (upstream, SRS 2022);
    md_linux.S compiles empty on aarch64 via its #if guards.  No ASM patching
    is needed.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

required_version = "1.9.5"


class SrsstateConan(ConanFile):
    name = "srs-state"
    version = required_version
    description = (
        "State Threads library (libst) patched for SRS — coroutine-based "
        "user-space threading with epoll-based event scheduling"
    )
    license = "GPL-2.0-or-later OR MPL-1.1"
    homepage = "https://github.com/ossrs/state-threads/"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def requirements(self):
        pass  # libc only; no Conan dependencies (W0/R36 verified)

    def layout(self):
        basic_layout(self)
        # The Makefile lives in the source root and builds in-place
        # ($(TARGETDIR)/obj relative to it) — build in the source folder.
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Provides buildenv (PATH, CONFIG_SHELL, ...) from the OHOS profile.
        # Compiler and flags are NOT taken from shell env in build(): the
        # Makefile hardcodes its defaults, so we pass everything on the
        # make command line, resolved from self.conf / settings (R33).
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _ohos_make_vars(self, targetdir):
        """Resolve toolchain identifiers from Conan config (R33), validated
        on the OHOS aarch64 toolchain during adaptation."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        # Makefile runs `$(RANLIB) $@` with no operation flag, so llvm-ar
        # (which requires an explicit operation) cannot serve as RANLIB.
        ranlib = shutil.which("ranlib") or shutil.which("llvm-ranlib") or "ranlib"
        # Makefile: LDFLAGS = -shared -soname=$(SONAME) -lc  (bare -soname is
        # GNU-ld speak; the clang driver needs -Wl,-soname).  SONAME is fixed
        # by upstream: libst.so.MAJOR with MAJOR=1.
        ldflags = "-shared -Wl,-soname,libst.so.1 -lc"
        return (
            f"CC={cc} CXX={cxx} AR={ar} RANLIB={ranlib} LD={cc} "
            f"TARGETDIR={targetdir} LDFLAGS='{ldflags}'"
        )

    def build(self):
        apply_conandata_patches(self)
        # OHOS `uname -r` contains spaces; the fixed TARGETDIR keeps the
        # $(TARGETDIR)/%.o pattern rules intact (see module docstring).
        if self.settings.build_type == "Debug":
            lib_target, targetdir = "linux-debug", "LINUX_OHOS_DBG"
        else:
            lib_target, targetdir = "linux-optimized", "LINUX_OHOS_OPT"
        make_vars = self._ohos_make_vars(targetdir)
        static_only = "no" if self.options.shared else "yes"
        self.run(f"make -j1 {lib_target} STATIC_ONLY={static_only} {make_vars}")

        # -- Upstream official test suite (layer 1, TEST_QUALITY_SPEC §3.1) --
        # Bundled gtest-fit suite: 7 cases / 25 assertions.  It links the
        # freshly built libst.a from obj/ (symlinked to TARGETDIR).
        self.run(f"make -j1 linux-debug-utest STATIC_ONLY=yes {make_vars}")
        self.run("./obj/st_utest")

    def package(self):
        targetdir = (
            "LINUX_OHOS_DBG" if self.settings.build_type == "Debug" else "LINUX_OHOS_OPT"
        )
        src = os.path.join(self.source_folder, targetdir)
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")
        copy(self, "st.h", src=src, dst=incdir, keep_path=False)
        # libst.a is always produced (utest links it); ship it for static builds.
        if not self.options.shared:
            copy(self, "libst.a", src=src, dst=libdir, keep_path=False)
        else:
            # Real file + standard SONAME symlinks: libst.so.1.9 -> consumers
            # resolve libst.so.1 (SONAME) and libst.so (-lst link input).
            copy(self, "libst.so.1.9", src=src, dst=libdir, keep_path=False)
            os.symlink("libst.so.1.9", os.path.join(libdir, "libst.so.1"))
            os.symlink("libst.so.1", os.path.join(libdir, "libst.so"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["st"]
