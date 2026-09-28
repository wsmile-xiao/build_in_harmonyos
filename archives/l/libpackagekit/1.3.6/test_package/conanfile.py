#!/usr/bin/env python3
"""Conan test_package for libpackagekit 1.3.6 — real consumer test (R34).

Builds a small C program that links libpackagekit-glib2 via pkg-config
(generators: PkgConfigDeps emits packagekit-glib2.pc) and instantiates a
PkControl object to prove the library is usable at runtime.

Note: glib's sub-.pc files (gio-2.0.pc, gio-unix-2.0.pc, ...) are not emitted
by PkgConfigDeps; copy them from the glib package like the main recipe does.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LibpackagekitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("glib/2.84.0")

    def layout(self):
        basic_layout(self)

    def generate(self):
        # Copy ALL .pc from ALL dependency packages into generators_folder so
        # the full Requires chain (glib-2.0 -> gio-2.0/gio-unix-2.0/gobject-2.0
        # -> libpcre2-8/libffi) resolves with pkg-config.
        for dep in self.dependencies.values():
            try:
                dep_pkg = dep.package_folder
            except Exception:
                continue
            if not dep_pkg:
                continue
            pc_dir = os.path.join(dep_pkg, "lib", "pkgconfig")
            if not os.path.isdir(pc_dir):
                continue
            for name in os.listdir(pc_dir):
                if not name.endswith(".pc"):
                    continue
                dst = os.path.join(self.generators_folder, name)
                if not os.path.exists(dst):
                    shutil.copy2(os.path.join(pc_dir, name), dst)
                self._fix_pc_prefix(dst, dep_pkg)

    @staticmethod
    def _fix_pc_prefix(pc_path, prefix):
        if not os.path.isfile(pc_path):
            return
        data = open(pc_path, encoding="utf-8", errors="replace").read()
        data2 = re.sub(r"(?m)^prefix=.*$", "prefix=" + prefix, data, count=1)
        if data2 != data:
            open(pc_path, "w", encoding="utf-8").write(data2)

    def build(self):
        # CC comes from the Conan toolchain (conanbuild env), not a raw shell
        # variable (R33). PkgConfigDeps already injected pkg-config paths.
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c") or "clang"
        self.run(
            f'CC="{cc}" PKG_CONFIG_PATH="{self.generators_folder}" '
            f'pkg-config --cflags --libs packagekit-glib2 glib-2.0 gobject-2.0 '
            f'> {self.build_folder}/pkgflags.txt',
            env="conanbuild",
        )
        with open(os.path.join(self.build_folder, "pkgflags.txt")) as f:
            flags = f.read().strip()
        # pkg-config filters the -L/lib system dir; musl loader (ld-musl-*.so)
        # lives there and glib requires it — re-add explicitly.
        self.run(
            f'{cc} -o {self.build_folder}/test_libpackagekit '
            f'{os.path.join(self.source_folder, "test.c")} {flags} -L/lib',
            env="conanbuild",
        )

    def test(self):
        # LD_LIBRARY_PATH must include the tested package's lib dir
        # (shared lib). VirtualRunEnv covers deps; prepend ours explicitly.
        try:
            pkg_dir = self.dependencies["libpackagekit"].package_folder
            ld = os.path.join(pkg_dir, "lib")
        except Exception:
            ld = None
        env = {"LD_LIBRARY_PATH": ld} if ld else None
        self.run(f"{self.build_folder}/test_libpackagekit", env="conanrun", cwd=self.build_folder)
