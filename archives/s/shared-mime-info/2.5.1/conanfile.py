#!/usr/bin/env python3
"""Conan recipe for shared-mime-info 2.5.1 — freedesktop MIME database
builder (C, meson build, freedesktop source).

Adaptation lessons applied:
- meson build (freedesktop project — like pixman).
- meson needs ar + ninja: AR=/data/service/hnp/bin/llvm-ar, PATH prefers
  /data/service/hnp/bin (usr/local ninja Permission denied).
- xmlto (spec docs) missing locally: -Dbuild-spec=false skips it.
- Deps libxml2/glib resolved via PkgConfigDeps (meson uses pkg-config
  for libxml-2.0/glib-2.0 — local shell lacks them, conan provides).
- self.run env arg must be a list — use command-prefix env vars.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson


class SharedMimeInfoConan(ConanFile):
    name = "shared-mime-info"
    version = "2.5.1"
    description = "Freedesktop.org shared MIME-info database"
    license = "GPL-2.0"
    homepage = "https://freedesktop.org/wiki/Software/shared-mime-info/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "application"

    generators = "PkgConfigDeps"

    def requirements(self):
        self.requires("libxml2/2.15.3")
        self.requires("glib/2.84.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Upstream tests fix: tests/meson.build references test_tree_magic
        # (executable defined in src/meson.build inside `if gio.found()`) —
        # meson subdir vars don't propagate to sibling subdirs, so tests/
        # hits "Unknown variable". Define it at the ROOT meson.build before
        # subdir('src') so it reaches tests/ too, then enable build-tests.
        mb = os.path.join(self.source_folder, "meson.build")
        if os.path.isfile(mb):
            s = open(mb).read()
            anchor = "subdir('src')"
            decl = ("test_tree_magic = executable('tree-magic', "
                    "'src/test-tree-magic.c', "
                    "dependencies: [dependency('glib-2.0')], install: false)\n")
            if anchor in s and "test_tree_magic = executable" not in s.split(
                    anchor)[0]:
                open(mb, "w").write(s.replace(anchor, decl + anchor, 1))
        bd = os.path.join(self.source_folder, "builddir")
        pc = os.path.join(self.generators_folder)
        env = (f"PATH=/data/service/hnp/bin:$PATH PKG_CONFIG_PATH='{pc}' "
               "CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ "
               "AR=/data/service/hnp/bin/llvm-ar")
        # -Dbuild-spec=false: skip xmlto (spec docs); build-tests now ENABLED
        # (root test_tree_magic definition fixes the upstream tests config)
        self.run(f"{env} meson setup {bd} --buildtype=release "
                 f"-Dbuild-spec=false -Dbuild-tests=true",
                 cwd=self.source_folder)
        self.run(f"{env} ninja -C {bd}", cwd=self.source_folder)
        # L1: run upstream test suite (meson test) — real pass rate
        self.run(f"{env} meson test -C {bd}", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        # meson puts the binary under builddir/src/ — walk to locate it
        umd = None
        for root, _dirs, files in os.walk(os.path.join(src, "builddir")):
            if "update-mime-database" in files:
                umd = os.path.join(root, "update-mime-database")
                break
        if not umd:
            raise ConanException("update-mime-database binary missing")
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        shutil.copy2(umd, os.path.join(self.package_folder, "bin",
                                       "update-mime-database"))
        data = os.path.join(src, "data")
        if os.path.isdir(data):
            shutil.copytree(data, os.path.join(self.package_folder, "data"))

    def package_info(self):
        bindir = os.path.join(self.package_folder, "builddir")
        self.output.info(f"PATH={bindir}")
