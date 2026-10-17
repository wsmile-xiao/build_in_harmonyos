#!/usr/bin/env python3
"""Conan recipe for yascreen 2.13 — raw GNUmakefile build system.

yascreen is a small terminal screen control library. Upstream ships a `Makefile`
wrapper that re-executes itself through `gmake`, which does not exist on the
target, so the recipe drives `GNUmakefile` directly. The upstream build always
produces both `libyascreen.a` and `libyascreen.so.0.0.0`; `AR`/`RANLIB` are
passed on the command line to override the hardcoded `gcc-ar`/`gcc-ranlib`
(the clang toolchain has no gcc-ar). The `install` target is not used because
it depends on `go-md2man` to render the man page; the package step copies the
built artifacts instead.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class YascreenConan(ConanFile):
    name = "yascreen"
    version = "2.13"
    description = "Yet another screen library - terminal screen control library"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/bbonev/yascreen"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # yascreen builds in-source (GNUmakefile writes artifacts next to the sources)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler/tool names from Conan conf, never from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R5: OHOS has no /bin/sh guarantees; use CONFIG_SHELL from profile [buildenv].
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # Upstream `Makefile` is only a wrapper demanding gmake; call GNUmakefile
        # directly. Command-line AR/RANLIB override the hardcoded gcc-ar/gcc-ranlib.
        # Upstream flags are self-probing (-flto=auto is dropped when unsupported).
        # PREFIX only affects the generated yascreen.pc paths.
        self.run(
            f"make -f GNUmakefile CC={cc} AR=llvm-ar RANLIB=llvm-ranlib "
            f"SHELL={config_shell} PREFIX={self.package_folder} all -j1",
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "yascreen.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        libdir = os.path.join(self.package_folder, "lib")
        # Ship the artifact selected by the `shared` option. Upstream always
        # builds both, but keeping both in lib/ makes the linker pick the .so
        # even for static consumers; musl ignores DT_RUNPATH so the test binary
        # then fails to load the versioned soname at runtime.
        if self.options.shared:
            copy(self, "libyascreen.so.0.0.0", src=self.source_folder, dst=libdir, keep_path=False)
            real = os.path.join(libdir, "libyascreen.so.0.0.0")
            for name in ("libyascreen.so.0", "libyascreen.so"):
                link = os.path.join(libdir, name)
                if os.path.lexists(link):
                    os.remove(link)
                os.symlink(os.path.basename(real), link)
        else:
            copy(self, "libyascreen.a", src=self.source_folder, dst=libdir, keep_path=False)
        copy(self, "yascreen.pc", src=self.source_folder,
             dst=os.path.join(libdir, "pkgconfig"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["yascreen"]
        self.cpp_info.set_property("pkg_config_name", "yascreen")
