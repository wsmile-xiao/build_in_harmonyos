#!/usr/bin/env python3
"""Conan recipe for asymptote 3.12 — Autotools build system (configure + make).

Asymptote is a powerful descriptive vector graphics language for technical
drawing, providing a natural coordinate-based framework. Labels and equations
are typeset by LaTeX, producing high-quality PostScript/PDF output.

Build: ./configure && make && make install
Product: `asy` executable (vector graphics compiler — no linkable library)
Build system: autotools (configure + make)

Adaptation notes (OHOS / HarmonyOS PC aarch64):
- gsl/2.8, zlib/1.3.1.1, gc/8.2.12, readline/8.3 are pulled from the
  ohpcd artifact repository (W0/R36). System-name libs (zlib/readline/
  ncurses) are forced static (R26) so no .so leaks into /system paths.
- The bundled Boehm GC (gc/ 8.2.8 subdir) fails to link on OHOS because
  it references pthread_setcancelstate/pthread_cancel which are absent
  from the OHOS sysroot libc (undefined symbols at link time).  We use the
  published conan gc/8.2.12 instead: its static libgc.a has no such
  references.  The bundled gc sources remain available under gc/ so that
  LspCpp (built in-source) can use them for its Boehm-GC C++ wrapper
  headers; the actual libgc.a linked into asy is the conan one, passed to
  make through the GCLIB/GCINCLUDE command-line variables (the Makefile
  was patched to use `GCLIB ?=` / `GCINCLUDE ?=` so they can be overridden).
- config.guess cannot identify HarmonyOS, so --build=aarch64-unknown-linux-gnu
  is passed on OHOS (autotools convention).
- OpenGL / Vulkan renderer shims are disabled on OHOS (no libglfw / vulkan
  SDK in the toolchain); LSP (LspCpp) stays enabled.
- make is invoked with --jobserver-style=pipe because OHOS disallows the
  GNU make FIFO jobserver.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.env import Environment


class AsymptoteConan(ConanFile):
    name = "asymptote"
    version = "3.12"
    description = "A powerful descriptive vector graphics language for technical drawing"
    license = "LGPL-3.0-or-later"
    homepage = "https://asymptote.sourceforge.io/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {
        "shared": False,
        "fPIC": True,
        # R26: system-name libraries forced static (no .so into /lib on OHOS).
        # zlib/readline/ncurses are OHOS system libs -> static only.
        # gsl is NOT an OHOS system lib: the ohpcd repo publishes only the
        # shared gsl/2.8 binary, so gsl stays shared (Conan-managed runtime).
        "zlib/*:shared": False,
        "readline/*:shared": False,
        "ncurses/*:shared": False,
        "gc/*:shared": False,
    }

    def config_options(self):
        # asymptote 是可执行工具, OHOS 平台无需 shared 库选项
        if self.settings.os in ("OHOS", "Linux"):
            self.options.rm_safe("shared")
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
            self.options.rm_safe("shared")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("gsl/2.8")
        self.requires("zlib/1.3.1.1")
        self.requires("gc/8.2.12")
        self.requires("readline/8.3")  # pulls ncurses transitively (static)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # Feed dependency -I/-L/-l flags and pkg-config metadata into
        # configure/make (AutotoolsDeps + PkgConfigDeps).
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            # R26: system-name libraries must be static (see Gotchas table)
            # readline/ncurses/zlib are autotools libraries; force static so
            # no shared object is emitted into /lib or /lib64 on OHOS.
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        if self.settings.os == "OHOS":
            # config.guess cannot identify HarmonyOS; use a Linux triplet
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            # No libglfw / vulkan SDK in the OHOS toolchain
            tc.configure_args.append("--disable-gl")
            tc.configure_args.append("--disable-vulkan")
        tc.generate()
        # The in-tree LspCpp build (a nested cmake project invoked from the
        # top-level Makefile) needs to locate the conan zlib for its bundled
        # ixwebsocket; make the zlib package folder visible to find_package(ZLIB).
        zlib = self.dependencies["zlib"]
        self.buildenv.append("CMAKE_PREFIX_PATH", zlib.package_folder)
        self.buildenv.define("ZLIB_ROOT", zlib.package_folder)
        # gsl ships only shared libraries; configure's conftest runs compiled
        # programs, which fail with "Error loading shared library libgsl.so.28"
        # unless LD_LIBRARY_PATH points at the dependency lib dirs.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # asy links against the conan-provided Boehm GC (see notes).  The
        # bundled gc/ sources stay in-tree for LspCpp, but libgc.a comes from
        # the gc/8.2.12 package; pass its location via make variables that the
        # patched Makefile accepts (GCLIB ?= / GCINCLUDE ?=).
        gc = self.dependencies["gc"]
        gc_lib = os.path.join(gc.package_folder, "lib", "libgc.a")
        gc_inc = os.path.join(gc.package_folder, "include")
        # GCC toolchain env (CXX full path) is sourced by Autotools.
        make_args = [
            "--jobserver-style=pipe",
            "-j4",
            f"GCLIB={gc_lib}",
            f"GCINCLUDE=-I{gc_inc} -Igc/include",
        ]
        autotools.make(args=make_args)

    def package(self):
        gc = self.dependencies["gc"]
        gc_lib = os.path.join(gc.package_folder, "lib", "libgc.a")
        gc_inc = os.path.join(gc.package_folder, "include")
        autotools = Autotools(self)
        autotools.install(args=[
            f"GCLIB={gc_lib}",
            f"GCINCLUDE=-I{gc_inc} -Igc/include",
        ])

    def package_info(self):
        # asymptote 是可执行文件, 非可链接库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
