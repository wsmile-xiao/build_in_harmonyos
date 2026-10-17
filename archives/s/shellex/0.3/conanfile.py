#!/usr/bin/env python3
"""Conan recipe — shellex 0.3 (upstream plain Makefile, LD_PRELOAD launcher).

shellex consists of a small LD_PRELOAD library (shellex_preload.so), a
POSIX-sh launcher script generated from shellex.in via sed, a default rc
file and an urxvt helper script. The upstream `install` target additionally
creates SYSCONFDIR symlinks with absolute prefixes, which is meaningless
inside a conan package, so the package() step replicates the upstream
install layout with plain file copies instead.

The urxvt/zsh runtime expected by the wrapper script is not part of the
OHOS platform; the preload library is the core artifact and is what the
consumer test exercises.
"""
import os

from conan import ConanFile
from conan.tools.build import build_jobs
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class ShellexConan(ConanFile):
    name = "shellex"
    version = "0.3"
    description = "shellex — shell based launcher (LD_PRELOAD helper library)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Merovius/shellex"
    url = ""  # CI fills this
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        jobs = build_jobs(self)
        # CC must be passed explicitly: upstream relies on make's built-in
        # default `cc`, which does not exist on the OHOS toolchain.
        self.run(f"make -j{jobs} CC={cc} SED=sed", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        copy(self, "shellex", src=src,
             dst=os.path.join(pkg, "bin"), keep_path=False)
        copy(self, "preload/shellex_preload.so", src=src,
             dst=os.path.join(pkg, "lib", "shellex"), keep_path=False)
        copy(self, "conf/shellexrc", src=src,
             dst=os.path.join(pkg, "lib", "shellex"), keep_path=False)
        copy(self, "conf/[0-9][0-9]-*", src=src,
             dst=os.path.join(pkg, "lib", "shellex", "conf"), keep_path=False)
        copy(self, "urxvt/shellex", src=src,
             dst=os.path.join(pkg, "lib", "shellex", "urxvt"), keep_path=False)
        copy(self, "LICENSE", src=src,
             dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
